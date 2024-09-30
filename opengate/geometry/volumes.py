import re
import os
import numpy as np
import itk
import json
from anytree import NodeMixin
from scipy.spatial.transform import Rotation

import opengate_core as g4

from ..base import DynamicGateObject, process_cls
from . import solids
from ..utility import ensure_filename_is_str
from ..exception import fatal, warning
from ..image import write_itk_image
from ..image import update_image_py_to_cpp
from .utility import (
    vec_np_as_g4,
    rot_np_as_g4,
    ensure_is_g4_transform,
)
from ..decorators import requires_fatal, requires_attribute_fatal
from ..definitions import __world_name__, __gate_list_objects__
from ..actors.dynamicactors import (
    VolumeImageChanger,
    VolumeTranslationChanger,
    VolumeRotationChanger,
)
from .materials import create_density_img


def _setter_hook_user_info_rotation(self, rotation_user):
    """Internal function associated with user_info rotation to check its validity."""
    if rotation_user is None:
        rotation = [Rotation.identity().as_matrix()]
    elif isinstance(rotation_user, (np.matrix, np.ndarray)) and rotation_user.shape == (
        3,
        3,
    ):
        # user has provided a single rotation matrix
        rotation = [rotation_user]
    elif isinstance(rotation_user[0], (np.matrix, np.ndarray)) and all(
        [
            isinstance(r, (np.matrix, np.ndarray)) and r.shape == (3, 3)
            for r in rotation_user
        ]
    ):
        # user has provided a list of rotation matrices
        rotation = rotation_user
    else:
        fatal(
            f"The parameter 'rotation' should be a 3x3 array or matrix or a list of such arrays/matrices. "
            f"You provided {rotation_user} for volume {self.name}. "
        )
    return rotation


def _getter_hook_user_info_rotation(self, rotation):
    if len(rotation) == 1:
        return rotation[0]
    else:
        return rotation


def _setter_hook_user_info_translation(self, translation_user):
    # if the user passes a single 3-vector, its first entry will be a number
    # ensure that translation is a list of vectors
    if translation_user is None:
        translation = [np.zeros(3, dtype=float)]
    elif not isinstance(translation_user[0], (__gate_list_objects__, np.ndarray)):
        translation = [np.array(translation_user)]
    else:
        translation = np.array(translation_user)
    if not all([len(t) == 3 for t in translation]):
        fatal(
            f"The translation parameter must be a 3-vector or a list of 3-vectors, "
            f"e.g. [1,2,1] or [[2,4,3], [5,4,7]]. "
            f"For volume {self.name}, you provided: \n{translation_user} for volume {self.name}. "
        )
    return translation


def _getter_hook_user_info_translation(self, translation):
    if len(translation) == 1:
        return translation[0]
    else:
        return translation


def _setter_hook_user_info_mother(self, mother):
    """Hook to be attached to property setter of user info 'mother' in all volumes.

    Checks if new mother is actually different from stored one.\n
    If so, it also tries to inform the volume manager that the volume tree needs an update. \n
    This latter part only applies for volumes which have a volume manager, \n
    i.e. which have been added to a simulation.
    """
    # duck typing: allow volume objects or their name
    try:
        mother_name = mother.name
    except AttributeError:
        mother_name = mother
    if mother_name != self.user_info["mother"]:
        try:
            self.volume_manager._need_tree_update = True
        except AttributeError:
            pass
    return mother_name


def _setter_hook_voxel_materials(self, voxel_materials):
    # make a structured array (https://stackoverflow.com/a/44337962)
    vm = np.array(
        [tuple(row) for row in voxel_materials],
        dtype=np.dtype(
            {"names": ["lower", "upper", "material"], "formats": [float, float, "<U32"]}
        ),
    )
    np.sort(vm, order="lower")
    return vm


def _setter_hook_ensure_array(self, input):
    return np.asarray(input)  # becomes dtype='<U32'


# inherit from NodeMixin to turn the class into a tree node
class VolumeBase(DynamicGateObject, NodeMixin):
    """
    Store information about a geometry volume:
    - G4 objects: Solid, LogicalVolume, PhysicalVolume
    - user parameters: user_info
    - additional data such as: mother, material etc
    """

    user_info_defaults = {
        "mother": (
            __world_name__,
            {
                "doc": "Name of the mother volume.",
                "setter_hook": _setter_hook_user_info_mother,
            },
        ),
        "material": ("G4_AIR", {"doc": "Name of the material"}),
        "translation": (
            [[0, 0, 0]],
            {
                "doc": "3-component vector or list of such vectors defining the translation "
                "w.r.t. the mother. If translation is a list of vectors, "
                "the volume will be repeeted once for each translation vector.",
                "setter_hook": _setter_hook_user_info_translation,
                "getter_hook": _getter_hook_user_info_translation,
                "dynamic": True,
            },
        ),
        "color": (
            [1, 1, 1, 1],
            {
                "doc": (
                    "4 component vector defining the volume's color in visual rendering. "
                    "The first 3 entries are RBG, the 4th is visible/invisible (1 or 0). "
                )
            },
        ),
        "rotation": (
            [Rotation.identity().as_matrix()],
            {
                "doc": "3x3 rotation matrix or list of such matrices. "
                "The matrix (matrices) should be np.array or np.matrix."
                "If a list of matrices is provided, the volume will be repeated, "
                "once for each rotation vector.",
                "setter_hook": _setter_hook_user_info_rotation,
                "getter_hook": _getter_hook_user_info_rotation,
                "dynamic": True,
            },
        ),
        "build_physical_volume": (
            True,
            {
                "doc": "Boolean flag (True/False) whether G4 should build a physical volume.",
                "type": bool,
            },
        ),
    }

    def __init__(self, *args, template=None, **kwargs):
        # GateObject base class digests all user info provided as kwargs
        # template = kwargs.pop('template', None)
        super().__init__(*args, **kwargs)

        # if a template volume is provided, clone all user info items from it
        # except for the name of course
        if template is not None:
            # FIXME: consider using from_dictionary()
            self.copy_user_info(template)
            # put back user infos which were explicitly passed as keyword argument
            for k in self.user_info.keys():
                if k != "name" and k in kwargs:
                    setattr(self, k, kwargs[k])

        # this attribute is used internally for the volumes tree
        # do not set it manually!
        self.parent = None

        self._is_constructed = False
        self.volume_engine = None

        # G4 references
        self.g4_world_log_vol = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        # this list contains all physical volumes (in case of repeated volume)
        self.g4_physical_volumes = []
        self.g4_material = None

    def close(self):
        self.release_g4_references()
        self.volume_engine = None
        self._is_constructed = False
        super().close()

    def release_g4_references(self):
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        self.g4_physical_volumes = []
        self.g4_material = None

    def __getstate__(self):
        return_dict = super().__getstate__()
        # Reset the following references to None because they cannot be pickled
        # They created when running a simulation
        return_dict["g4_logical_volume"] = None
        return_dict["g4_vis_attributes"] = None
        return_dict["g4_physical_volumes"] = []
        return_dict["g4_material"] = None
        return_dict["volume_engine"] = None
        return_dict["_is_constructed"] = False
        return return_dict

    def __finalize_init__(self):
        super().__finalize_init__()
        # need to add this explicitly because anytree does not properly declare
        # the attribute __parent in the NodeMixin.__init__ which leads to falls warnings
        self.known_attributes.add("_NodeMixin__parent")
        self.known_attributes.add("_NodeMixin__children")

    def _update_node(self):
        """Internal method which retrieves the volume object
        from the volume manager based on the mother's name stored as user info 'mother'
        """
        try:
            self.parent = self.volume_manager.get_volume(self.mother)
        except KeyError:
            fatal(
                "Error while trying to update a volume tree node: \n"
                f"Mother volume of {self.name} should be {self.mother}, "
                f"but it cannot be found in the list of volumes in the volume manager."
                f"Known volumes are: \n{self.volume_manager.volumes}"
            )

    def _request_volume_tree_update(self):
        try:
            self.volume_manager.update_volume_tree()
        except AttributeError:
            fatal(
                f"Unable to determine the world volume to which volume named {self.name} belongs. "
                "Probably the volume has not yet been added to the simulation. "
            )

    # # FIXME: maybe store reference to simulation directly, rather than reference to volume_manager?
    @property
    def volume_manager(self):
        # It is not compulsory for a GateObject to belong to a simulation,
        # and the volume might therefore not have any reference to a volume manager
        # (e.g. in volumes created for boolean operations),
        # but without a simulation/volume_manager, the volume is not known to the simulation
        # and certain functionality is unavailable
        if self.simulation is not None:
            return self.simulation.volume_manager
        else:
            return None

    @property
    def volume_type(self):
        return type(self).__name__

    @property
    def world_volume(self):
        self._request_volume_tree_update()
        try:
            self.volume_manager.update_volume_tree()
        except AttributeError:
            fatal(
                f"Unable to determine the world volume to which volume named {self.name} belongs. "
                "Probably the volume has not yet been added to the simulation. "
            )
        try:
            return self.ancestors[
                1
            ]  # index 0 is the volume tree root, index 1 is world level
        except IndexError:  # if no ancestors, this is a world volume already
            return self

    @property
    def volume_depth_in_tree(self):
        self._request_volume_tree_update()
        return len(self.ancestors) - 1  # do not count the tree root

    @property
    def ancestor_volumes(self):
        self._request_volume_tree_update()
        return self.ancestors[1:]  # first item is volume tree root, not a real volume

    @property
    def children_volumes(self):
        self._request_volume_tree_update()
        return self.children

    @property
    def number_of_repetitions(self):
        return len(self.user_info["translation"])

    def get_g4_physical_volume(self, index):
        try:
            return self.g4_physical_volumes[index]
        except IndexError:
            fatal(
                f"No physical volume with repetition index {index} "
                f"found in volume {self.name}. "
            )

    @property
    def translation_list(self):
        """Utility property which always returns a list of translations,
        even if the volume is not repeated and has thus only one translation vector.
        """
        len_rot = len(self.user_info["rotation"])
        if len_rot > 1 and len(self.user_info["translation"]) == 1:
            return self.user_info["translation"] * len_rot
        else:
            return self.user_info["translation"]

    @property
    def rotation_list(self):
        """Utility property which always returns a list of rotations,
        even if the volume is not repeated and has thus only one rotation vector.
        """
        len_trans = len(self.user_info["translation"])
        if len_trans > 1 and len(self.user_info["rotation"]) == 1:
            return self.user_info["rotation"] * len_trans
        else:
            return self.user_info["rotation"]

    @property
    def g4_region(self):
        if self.g4_logical_volume is None:
            return None
        else:
            return self.g4_logical_volume.GetRegion()

    # shortcut to first physical volume
    # FIXME: remove this shortcut. confusingly similar to self.g4_physical_volumes
    @property
    def g4_physical_volume(self):
        return self.g4_physical_volumes[0]

    # shortcuts to G4 variants of user info items 'translation' and 'rotation'
    @property
    def g4_translation(self):
        return [vec_np_as_g4(t) for t in self.translation_list]

    @property
    def g4_rotation(self):
        try:
            return [rot_np_as_g4(r) for r in self.rotation_list]
        except Exception as e:
            fatal(
                f"Unable to create G4 rotation matrix in volume {self.name}. "
                f"\nOriginal error message: {e}."
            )

    @property
    def g4_transform(self):
        g4_translation = self.g4_translation
        g4_rotation = self.g4_rotation
        if len(g4_translation) != len(g4_rotation):
            fatal(
                f"The number of translation vectors and rotation matrices in volume '{self.name}' does not match. "
                f"I found {len(g4_translation)} translations and {len(g4_rotation)} rotations. "
            )
        return [
            ensure_is_g4_transform(t, r) for t, r in zip(g4_translation, g4_rotation)
        ]

    # shortcut to the G4LogicalVolume of the mother
    @property
    def mother_g4_logical_volume(self):
        if self.mother is None:
            return None
        else:
            return g4.G4LogicalVolumeStore.GetInstance().GetVolume(self.mother, False)

    @property
    def mother_volume(self):
        self._update_node()
        return self.parent

    def construct(self):
        if self._is_constructed is False:
            self.construct_material()
            self.construct_solid()
            self.construct_logical_volume()
            # check user info:
            if self.build_physical_volume is True:
                self.construct_physical_volume()
            self._is_constructed = True

    def construct_material(self):
        if self.volume_manager is None:
            fatal(
                f"The volume {self.name} does not seem to be added to the simulation. "
                f"Use sim.volume_manager.add_volume(...) to add it. "
            )
        # retrieve or build the material
        if self.material is None:
            self.g4_material = None
        else:
            self.g4_material = self.volume_manager.find_or_build_material(self.material)

    @requires_attribute_fatal("g4_solid")
    @requires_fatal("g4_material")
    def construct_logical_volume(self):
        self.g4_logical_volume = g4.G4LogicalVolume(
            self.g4_solid, self.g4_material, self.name
        )
        # color
        self.g4_vis_attributes = g4.G4VisAttributes()
        self.g4_vis_attributes.SetColor(*self.color)
        self.g4_vis_attributes.SetVisibility(bool(self.color[3]))
        self.g4_logical_volume.SetVisAttributes(self.g4_vis_attributes)

    def construct_physical_volume(self):
        g4_transform = self.g4_transform
        if len(g4_transform) > 1:
            fatal(
                f"The volume named {self.name} of type {type(self).__name__} is not repeatable. "
                f"You may therefore only provide a single translation and/or rotation vector. "
            )
        self.g4_physical_volumes = [
            self._make_physical_volume(self.name, g4_transform[0])
        ]

    @requires_fatal("volume_manager")
    def _make_physical_volume(self, volume_name, g4_transform, copy_index=0):
        return g4.G4PVPlacement(
            g4_transform,
            self.g4_logical_volume,  # logical volume
            volume_name,  # volume name
            self.mother_g4_logical_volume,  # mother volume or None if World
            False,  # no boolean operation # FIXME for BooleanVolume ?
            copy_index,  # copy number
            self.volume_manager.simulation.check_volumes_overlap,
        )  # overlaps checking

    def create_changers(self):
        changers = super().create_changers()
        for dp in self.dynamic_params.values():
            if dp["extra_params"]["auto_changer"] is True:
                if "translation" in dp:
                    new_changer = VolumeTranslationChanger(
                        name=f"{self.name}_volume_translation_changer_{len(changers)}",
                        translations=dp["translation"],
                        attached_to=self,
                        simulation=self.simulation,
                        repetition_index=dp["extra_params"].pop("repetition_index", 0),
                    )
                    changers.append(new_changer)
                if "rotation" in dp:
                    new_changer = VolumeRotationChanger(
                        name=f"{self.name}_volume_rotation_changer_{len(changers)}",
                        rotations=dp["rotation"],
                        attached_to=self,
                        simulation=self.simulation,
                        repetition_index=dp["extra_params"].pop("repetition_index", 0),
                    )
                    changers.append(new_changer)
            else:
                warning(
                    f"You need to manually create a changer for dynamic parametrisation {dp} "
                    f"of volume '{self.name}'."
                )
        return changers

    # set physical properties in this (logical) volume
    # behind the scenes, this will create a region and associate this volume with it
    @requires_fatal("volume_manager")
    def set_production_cut(self, particle_name, value):
        self.volume_manager.simulation.physics_manager.set_production_cut(
            self.name, particle_name, value
        )

    @requires_fatal("volume_manager")
    def set_max_step_size(self, max_step_size):
        self.volume_manager.simulation.physics_manager.set_max_step_size(
            self.name, max_step_size
        )

    @requires_fatal("volume_manager")
    def set_max_track_length(self, max_track_length):
        self.volume_manager.simulation.physics_manager.set_max_track_length(
            self.name, max_track_length
        )

    @requires_fatal("volume_manager")
    def set_min_ekine(self, min_ekine):
        self.volume_manager.simulation.physics_manager.set_min_ekine(
            self.name, min_ekine
        )

    @requires_fatal("volume_manager")
    def set_max_time(self, max_time):
        self.volume_manager.simulation.physics_manager.set_max_time(self.name, max_time)

    @requires_fatal("volume_manager")
    def set_min_range(self, min_range):
        self.volume_manager.simulation.physics_manager.set_min_range(
            self.name, min_range
        )


class RepeatableVolume(VolumeBase):
    def get_repetition_name_from_index(self, index):
        return f"{self.name}_rep_{index}"

    def get_repetition_index_from_name(self, name):
        suffix = re.findall(r"_rep_\d+", name)
        if len(suffix) != 1:
            fatal(
                f"Something went wrong while trying to determine the repetition index "
                f"from repetition name {name} in volume {self.name}."
            )
        else:
            suffix = suffix[0]
        return int(suffix.lstrip("rep_"))

    def construct_physical_volume(self):
        g4_transform = self.g4_transform
        if len(g4_transform) > 1:
            self.g4_physical_volumes = []  # reset list to empty
            for i, g4t in enumerate(g4_transform):
                self.g4_physical_volumes.append(
                    self._make_physical_volume(
                        self.get_repetition_name_from_index(i),
                        g4t,
                        copy_index=i,
                    ),
                )
        else:
            super().construct_physical_volume()

    def add_dynamic_parametrisation(self, repetition_index=0, **params):
        super().add_dynamic_parametrisation(repetition_index=repetition_index, **params)


class BooleanVolume(RepeatableVolume, solids.BooleanSolid):
    """Volume resulting from a boolean operation of the solids contained in two volumes."""


# Function to handle boolean operations on volumes
# They create a new volume object, but the actual g4_solid is only created when the volume's
# construct() method is invoked
def _make_boolean_volume(
    volume_1, volume_2, operation, translation=None, rotation=None, new_name=None
):
    name_joiners = {"intersect": "times", "add": "plus", "subtract": "minus"}
    if operation not in name_joiners.keys():
        fatal("Unknown boolean operation. ")
    if new_name is None:
        new_name = f"({volume_1.name}_{name_joiners[operation]}_{volume_2.name})"

    if rotation is None:
        rotation = Rotation.identity().as_matrix()
    if translation is None:
        translation = [0, 0, 0]

    new_volume = BooleanVolume(name=new_name, template=volume_1)
    # need to access the user_info dict directly because the property 'creator_volumes' is read-only
    new_volume.user_info["creator_volumes"] = [volume_1, volume_2]
    new_volume.rotation_boolean_operation = rotation
    new_volume.translation_boolean_operation = translation
    new_volume.operation = operation
    return new_volume


def intersect_volumes(
    volume_1, volume_2, translation=None, rotation=None, new_name=None
):
    return _make_boolean_volume(
        volume_1,
        volume_2,
        "intersect",
        translation=translation,
        rotation=rotation,
        new_name=new_name,
    )


def unite_volumes(volume_1, volume_2, translation=None, rotation=None, new_name=None):
    return _make_boolean_volume(
        volume_1,
        volume_2,
        "add",
        translation=translation,
        rotation=rotation,
        new_name=new_name,
    )


def subtract_volumes(
    volume_1, volume_2, translation=None, rotation=None, new_name=None
):
    return _make_boolean_volume(
        volume_1,
        volume_2,
        "subtract",
        translation=translation,
        rotation=rotation,
        new_name=new_name,
    )


# **** Specific CSG volumes ****
# They are defined by inheriting from the corresponding solid class
# Nothing else needs to be implemented here.


class BoxVolume(RepeatableVolume, solids.BoxSolid):
    """Volume with a box shape."""


class HexagonVolume(RepeatableVolume, solids.HexagonSolid):
    """Volume with a hexagon shape."""


class ConsVolume(RepeatableVolume, solids.ConsSolid):
    """Volume with the shape of a cone or conical section."""


class PolyhedraVolume(RepeatableVolume, solids.PolyhedraSolid):
    """Volume with a polyhedral shape."""


class SphereVolume(RepeatableVolume, solids.SphereSolid):
    """Volume with a sphere or spherical shell shape."""


class TrapVolume(RepeatableVolume, solids.TrapSolid):
    """Volume with a generic trapezoidal shape."""


class TrdVolume(RepeatableVolume, solids.TrdSolid):
    """Volume with a symmetric trapezoidal shape."""


class TubsVolume(RepeatableVolume, solids.TubsSolid):
    """Volume with a tube or cylindrical section shape."""


class TesselatedVolume(RepeatableVolume, solids.TesselatedSolid):
    """Volume based on a mesh volume by reading an STL file."""


class RepeatParametrisedVolume(VolumeBase):
    """
    Volume created from another volume via translations.
    """

    user_info_defaults = {
        "linear_repeat": (
            [1, 1, 1],
            {"doc": "FIXME"},
        ),
        "offset": (
            [0, 0, 0],
            {"doc": "3 component vector or list."},
        ),
        "offset_nb": (1, {"doc": "FIXME"}),
        "start": ("auto", {"doc": "FIXME"}),
    }

    def __init__(self, repeated_volume, *args, **kwargs):
        # FIXME: This should probably be a user_info
        self.repeated_volume = repeated_volume
        if "name" not in kwargs:
            kwargs["name"] = f"{repeated_volume.name}_param"
        kwargs["mother"] = repeated_volume.mother
        super().__init__(*args, **kwargs)
        if repeated_volume.build_physical_volume is True:
            repeated_volume.build_physical_volume = False
        self.g4_repeat_parametrisation = None

    def close(self):
        self.repeated_volume.close()
        super().close()

    def release_g4_references(self):
        super().release_g4_references()
        # FIXME: unsure. If not set to None, we get the following error:
        # "cannot pickle 'opengate_core.opengate_core.GateRepeatParameterisation' object"
        self.g4_repeat_parametrisation = None

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_repeat_parametrisation"] = None
        return return_dict

    def construct(self):
        if self._is_constructed is False:
            # construct the repeated volume,
            # it will not construct the phys volume because that was disabled in init()
            self.repeated_volume.construct()
            # construct the physical volume of this repeat parametrised volume
            self.construct_physical_volume()
            self._is_constructed = True

    def construct_physical_volume(self):
        # check if the mother is the world
        if self.mother_g4_logical_volume is None:
            fatal(f"The mother of {self.name} cannot be the world.")

        self.create_repeat_parametrisation()

        # number of copies
        n = (
            self.linear_repeat[0]
            * self.linear_repeat[1]
            * self.linear_repeat[2]
            * self.offset_nb
        )

        # (only daughter)
        # g4.EAxis.kUndefined => faster
        self.g4_physical_volumes.append(
            g4.G4PVParameterised(
                self.name,
                self.repeated_volume.g4_logical_volume,  # logical volume from the repeated volume
                self.mother_g4_logical_volume,
                g4.EAxis.kUndefined,
                n,
                self.g4_repeat_parametrisation,
                False,  # very slow if True
            )
        )

    def create_repeat_parametrisation(self):
        if self.start == "auto":
            self.start = [
                -(x - 1) * y / 2.0 for x, y in zip(self.linear_repeat, self.translation)
            ]
        # create parameterised
        keys = [
            "linear_repeat",
            "start",
            "translation",
            "rotation",
            "offset",
            "offset_nb",
        ]
        if self.number_of_repetitions > 1:
            fatal(
                f"The {type(self).name} volume named '{self.name}' has multiple translations/rotations, "
                f"but only one is allowed."
            )
        p = {}
        for k in keys:
            p[k] = getattr(self, k)
        self.g4_repeat_parametrisation = g4.GateRepeatParameterisation()
        self.g4_repeat_parametrisation.SetUserInfo(p)


class ImageVolume(VolumeBase, solids.ImageSolid):
    """
    Store information about a voxelized volume
    """

    user_info_defaults = {
        "voxel_materials": (
            [[-np.inf, np.inf, "G4_AIR"]],
            {
                "doc": "FIXME",
            },
        ),
        "image": (
            "",
            {"doc": "Path to the image file", "is_input_file": True, "dynamic": True},
        ),
        "dump_label_image": (
            None,
            {
                "doc": "Path at which the image containing material labels should be saved. "
                "Set to None to dump no image."
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # look up table MATERIAL -> LABEL
        self.material_to_label_lut = None

        # ITK images
        self.itk_image = None  # the input
        self.label_image = None  # image storing material labels
        # G4 references (additionally to those in base class)
        self.g4_physical_x = None
        self.g4_physical_y = None
        self.g4_physical_z = None
        self.g4_logical_x = None
        self.g4_logical_y = None
        self.g4_logical_z = None
        self.g4_voxel_param = None

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_physical_x"] = None
        return_dict["g4_physical_y"] = None
        return_dict["g4_physical_z"] = None
        return_dict["g4_logical_x"] = None
        return_dict["g4_logical_y"] = None
        return_dict["g4_logical_z"] = None
        return_dict["g4_voxel_param"] = None
        return return_dict

    def close(self):
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_logical_x = None
        self.g4_logical_y = None
        self.g4_logical_z = None
        self.g4_physical_x = None
        self.g4_physical_y = None
        self.g4_physical_z = None
        self.g4_voxel_param = None

    # @requires_fatal('itk_image')
    # FIXME: replace this property by function in opengate.image
    @property
    def size_pix(self):
        return np.array(itk.size(self.itk_image)).astype(int)

    # @requires_fatal('itk_image')
    # FIXME: replace this property by function in opengate.image
    @property
    def spacing(self):
        return np.array(self.itk_image.GetSpacing())

    # @requires_fatal("itk_image")
    @property
    def native_translation(self):
        if self.itk_image is not None:
            origin = np.array(self.itk_image.GetOrigin())
            spacing = np.array(self.itk_image.GetSpacing())
            size = np.array(self.itk_image.GetLargestPossibleRegion().GetSize())
            center = (size - 1.0) * spacing / 2.0
            return origin + Rotation.from_matrix(self.native_rotation).apply(center)
        else:
            return None

    # @requires_fatal("itk_image")
    @property
    def native_rotation(self):
        if self.itk_image is not None:
            return np.array(self.itk_image.GetDirection())
        else:
            return None

    @requires_fatal("volume_engine")
    def construct(self):
        self.material_to_label_lut = self.create_material_to_label_lut()
        # make sure the materials are created in Geant4
        for m in self.material_to_label_lut:
            self.volume_manager.find_or_build_material(m)
        self.itk_image = self.read_input_image()
        self.label_image = self.create_label_image()
        if self.dump_label_image:
            self.save_label_image()
        # set attributes of the solid
        self.half_size_mm = 0.5 * self.size_pix * self.spacing
        self.half_spacing = 0.5 * self.spacing
        self.construct_material()
        self.construct_solid()
        self.construct_logical_volume()
        self.g4_voxel_param = self.create_image_parametrisation()
        self.construct_physical_volume()

    def construct_physical_volume(self):
        super().construct_physical_volume()

        self.g4_physical_y = g4.G4PVReplica(
            self.name + "_Y",
            self.g4_logical_y,
            self.g4_logical_volume,
            g4.EAxis.kYAxis,
            self.size_pix[1],  # nReplicas
            self.spacing[1],  # width
            0.0,
        )  # offset

        # param X
        self.g4_physical_x = g4.G4PVReplica(
            self.name + "_X",
            self.g4_logical_x,
            self.g4_logical_y,
            g4.EAxis.kXAxis,
            self.size_pix[0],
            self.spacing[0],
            0.0,
        )

        self.g4_physical_z = g4.G4PVParameterised(
            self.name + "_Z",
            self.g4_logical_z,
            self.g4_logical_x,
            g4.EAxis.kZAxis,  # g4.EAxis.kUndefined, ## FIXME ?
            self.size_pix[2],
            self.g4_voxel_param,
            False,
        )  # overlaps checking

    def construct_logical_volume(self):
        super().construct_logical_volume()
        self.g4_logical_x = g4.G4LogicalVolume(
            self.g4_solid_x, self.g4_material, self.name + "_log_X"
        )
        self.g4_logical_y = g4.G4LogicalVolume(
            self.g4_solid_y, self.g4_material, self.name + "_log_Y"
        )
        self.g4_logical_z = g4.G4LogicalVolume(
            self.g4_solid_z, self.g4_material, self.name + "_log_Z"
        )

    def create_material_to_label_lut(self, material=None, voxel_materials=None):
        if voxel_materials is None:
            voxel_materials = self.voxel_materials
        if material is None:
            material = self.material
        # prepare a LUT from material name to label
        material_to_label_lut = {}
        material_to_label_lut[material] = 0  # initialize with label 0

        # sort voxel_materials according to lower bounds
        voxel_materials_sorted = sorted(voxel_materials, key=lambda x: x[0])

        lower_bounds = np.array([row[0] for row in voxel_materials_sorted])
        upper_bounds = np.array([row[1] for row in voxel_materials_sorted])
        if not (lower_bounds[1:] >= upper_bounds[:-1]).all():
            fatal(f"Overlapping intervals in voxel_materials of volume {self.name}.")

        # fill the LUT
        i = 1
        for row in voxel_materials_sorted:
            if row[2] not in material_to_label_lut:
                material_to_label_lut[row[2]] = i
                i += 1

        return material_to_label_lut

    def read_input_image(self, path=None):
        if path is None:
            itk_image = itk.imread(ensure_filename_is_str(self.image))
            self.itk_image = itk_image
        else:
            itk_image = itk.imread(ensure_filename_is_str(path))
        return itk_image

    def create_label_image(self, itk_image=None):
        # read image
        if itk_image is None:
            if self.itk_image is None:
                self.itk_image = self.read_input_image()
            itk_image = self.itk_image

        if self.material_to_label_lut is None:
            self.material_to_label_lut = self.create_material_to_label_lut()

        # sort voxel_materials according to lower bounds
        voxel_materials_sorted = sorted(self.voxel_materials, key=lambda x: x[0])

        # find gaps in the voxels materials intervals
        # upper bounds that are not also lower bounds of the subsequent interval
        bins = [row[0] for row in voxel_materials_sorted]
        # additional bins are those where an upper interval boundary
        # does not correspond to the next lower interval boundary
        additional_bins = set([row[1] for row in voxel_materials_sorted]).difference(
            bins
        )
        bins.extend(additional_bins)
        labels = [self.material_to_label_lut[row[2]] for row in voxel_materials_sorted]
        labels.extend(
            len(additional_bins) * [0]
        )  # additional bins should have label 0,
        # i.e. the volume's standard material
        # np.digitize function requires bins in ascending order -> sort
        bins_sorted = []
        labels_sorted = [0]  # label 0 for voxel values below lowest interval
        for b, l in sorted(zip(bins, labels), key=lambda pair: pair[0]):
            bins_sorted.append(b)
            labels_sorted.append(l)

        # get numpy array view of input itk image
        input_image = itk.array_view_from_image(itk_image)

        label_image_arr = np.array(labels_sorted, dtype=np.ushort)[
            np.digitize(input_image, bins=bins_sorted)
        ]

        label_image = itk.image_from_array(label_image_arr)
        label_image.CopyInformation(itk_image)
        return label_image

    def create_image_parametrisation(self, label_image=None):
        if label_image is None:
            if self.label_image is None:
                self.label_image = self.create_label_image()
            label_image = self.label_image
        # initialize parametrisation
        g4_voxel_param = g4.GateImageNestedParameterisation()

        # send image to cpp size
        update_image_py_to_cpp(label_image, g4_voxel_param.cpp_edep_image, True)
        g4_voxel_param.initialize_image()
        g4_voxel_param.initialize_material(list(self.material_to_label_lut.keys()))

        return g4_voxel_param

    def update_label_image(self, label_image):
        """Needed for dynamic image parametrisation."""
        # send image to cpp size
        update_image_py_to_cpp(label_image, self.g4_voxel_param.cpp_edep_image, True)
        self.g4_voxel_param.initialize_image()

    def save_label_image(self, path=None):
        # dump label image ?
        if path is None:
            if self.volume_manager is None:
                fatal(
                    f"Cannot save label image of ImageVolume {self.name}. "
                    f"Either provide a path or add the volume to the simulation. "
                )
            root, ext = os.path.splitext(self.dump_label_image)
            # path = (
            #    self.volume_manager.simulation.get_output_path()
            #    / f"label_to_material_lut_{self.name}.json"
            # )
            path = root + ".json"
        if self.label_image is None:
            self.create_label_image()

        self.label_image.SetOrigin(self.itk_image.GetOrigin())  # set origin as in input
        # FIXME: should write image into output dir
        write_itk_image(self.label_image, str(self.dump_label_image))
        with open(path, "w") as f:
            json.dump(self.material_to_label_lut, f)

        # re-compute image origin such that it is centered at 0
        self.label_image.SetOrigin(
            -(self.size_pix * self.spacing) / 2.0 + self.spacing / 2.0
        )

    def create_density_image(self):
        return create_density_img(
            self, self.volume_manager.material_database.g4_materials
        )

    def create_changers(self):
        # get the changers from the mother classes and append those specific to the ImageVolume class
        changers = super().create_changers()
        counter = 0
        for dp in self.dynamic_params.values():
            if dp["extra_params"]["auto_changer"] is True:
                if "image" in dp:
                    # create a LUT of image parametrisations
                    label_image = {}
                    for path_to_image in set(dp["image"]):
                        itk_image = self.read_input_image(path_to_image)
                        label_image[path_to_image] = self.create_label_image(itk_image)
                    new_changer = VolumeImageChanger(
                        name=f"{self.name}_volume_image_changer_{len(changers)}",
                        attached_to=self,
                        simulation=self.simulation,
                        images=dp["image"],
                        label_image=label_image,
                    )
                    changers.append(new_changer)
                    counter += 1
            else:
                warning(
                    f"You need to manually create a changer for dynamic parametrisation {dp} "
                    f"of volume '{self.name}'."
                )
        if counter > 1:
            warning(
                f"You have provided multiple dynamic image parametrisation (4D image) "
                f"in the {type(self).__name__} named {self.name}. "
                f"Consider verifying if this is intentional. "
            )
        return changers


class ParallelWorldVolume(NodeMixin):
    def __init__(self, name, volume_manager):
        super().__init__()
        self.name = name
        self.volume_manager = volume_manager
        # the volume manager is guaranteed to have a volume_tree_root because it is created in __init__
        self.parent = self.volume_manager.volume_tree_root

        # it is attached to the parallel world engine, instead of the volume engine as other volumes
        self.parallel_world_engine = None

        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

    def release_g4_references(self):
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

    def close(self):
        self.release_g4_references()
        self.parallel_world_engine = None

    def __getstate__(self):
        return_dict = self.__dict__
        return_dict["g4_world_phys_vol"] = None
        return_dict["g4_world_log_vol"] = None
        return_dict["parallel_world_engine"] = None
        return return_dict

    @requires_fatal("parallel_world_engine")
    def construct(self):
        # get the physical volume through the parallel world engine
        # do not construct it
        self.g4_world_phys_vol = self.parallel_world_engine.GetWorld()
        self.g4_world_log_vol = self.g4_world_phys_vol.GetLogicalVolume()

    # need this dummy method because the parent attribute should not be updated
    def _update_node(self):
        pass


# inherit from NodeMixin turn the class into a tree node
class VolumeTreeRoot(NodeMixin):
    """Small class to provide a root for the volume tree."""

    def __init__(self, volume_manager) -> None:
        super().__init__()
        self.volume_manager = volume_manager
        self.name = "volume_tree_root"
        self.parent = None  # None means this is a tree root

    def __getstate__(self):
        return_dict = self.__dict__
        return_dict["volume_engine"] = None
        return return_dict


# The following lines make sure that all classes which
# inherit from the GateObject base class are processed upon importing opengate.
# In this way, all properties corresponding to the class's user_info dictionary
# will be created.
# This ensures, e.g., that auto-completion in interactive python consoles
# and code editors suggests the properties.
process_cls(VolumeBase)
process_cls(BooleanVolume)
process_cls(RepeatableVolume)
process_cls(BoxVolume)
process_cls(HexagonVolume)
process_cls(ConsVolume)
process_cls(PolyhedraVolume)
process_cls(SphereVolume)
process_cls(TrapVolume)
process_cls(TrdVolume)
process_cls(TubsVolume)
process_cls(RepeatParametrisedVolume)
process_cls(ImageVolume)
process_cls(TesselatedVolume)
