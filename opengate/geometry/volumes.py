import numpy as np
import itk
from box import BoxList
from anytree import NodeMixin
from scipy.spatial.transform import Rotation

import opengate_core as g4

from ..base import GateObject, process_cls
from . import solids
from ..utility import check_filename_type
from ..exception import fatal, warning
from ..image import create_3d_image, update_image_py_to_cpp
from .utility import (
    vec_np_as_g4,
    rot_np_as_g4,
    get_g4_transform,
)
from ..decorators import requires_warning, requires_fatal, requires_attribute_fatal
from ..definitions import __world_name__


def _setter_hook_user_info_rotation(self, rotation):
    """Internal function associated with user_info rotation to check its validity."""
    if rotation is None:
        return Rotation.identity().as_matrix()
    elif not isinstance(rotation, (np.matrix, np.ndarray)) or rotation.shape != (3, 3):
        fatal("The user info 'rotation' should be a 3x3 array or matrix.")
    else:
        return rotation


def _setter_hook_user_info_mother(self, mother):
    """Hook to be attached to property setter of user info 'mother' in all volumes.

    Checks if new mother is actually different from stored one.\n
    If so, it also tries to inform the volume manager that the volume tree needs an update. \n
    This latter part only applies for volumes which have a volume manager, \n
    i.e. which have been added to a simulation.
    """
    if mother != self.user_info["mother"]:
        try:
            self.volume_manager._need_tree_update = True
        except AttributeError:
            pass
    return mother


def _setter_hook_repeat(self, repeat):
    if not isinstance(repeat, BoxList):
        return BoxList(repeat)
    else:
        return repeat


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
class VolumeBase(GateObject, NodeMixin):
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
            [0, 0, 0],
            {"doc": "3 component vector defining the translation w.r.t. the mother."},
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
            Rotation.identity().as_matrix(),
            {
                "doc": "3x3 rotation matrix. Should be np.array or np.matrix.",
                "setter_hook": _setter_hook_user_info_rotation,
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

    def __init__(self, *args, **kwargs):
        # Volume_manager is not compulsory when creating a volume, e.g. for boolean operations,
        # but without a volume_manager, the volume is not known to the simulation
        # and certain functionality is unavailable
        try:
            self.volume_manager = kwargs["volume_manager"]
        except KeyError:
            self.volume_manager = None

        # GateObject base class digests all user info provided as kwargs
        super().__init__(*args, **kwargs)

        # if a template volume is provided, clone all user info items from it
        # except for the name of course
        if "template" in kwargs:
            self.clone_user_info(kwargs["template"])
            # put back user infos which were explicitly passed as keyword argument
            for k in self.user_info.keys():
                if k != "name":
                    try:
                        setattr(self, k, kwargs[k])
                    except KeyError:
                        pass

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

    def release_g4_references(self):
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        self.g4_physical_volumes = []
        self.g4_material = None

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
    def g4_region(self):
        if self.g4_logical_volume is None:
            return None
        else:
            return self.g4_logical_volume.GetRegion()

    # shortcut to first physical volume
    @property
    def g4_physical_volume(self):
        return self.g4_physical_volumes[0]

    # shortcuts to G4 variants of user info items 'translation' and 'rotation'
    @property
    def g4_translation(self):
        return vec_np_as_g4(self.translation)

    @property
    def g4_rotation(self):
        return rot_np_as_g4(self.rotation)

    @property
    def g4_transform(self):
        return get_g4_transform(self.translation, self.rotation)

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
        self.g4_physical_volumes.append(self._make_physical_volume(self.name))

    @requires_fatal("volume_engine")
    def _make_physical_volume(self, volume_name, copy_index=0, transform=None):
        if transform is None:
            g4_transform = self.g4_transform
        else:
            if isinstance(transform, g4.G4Transform3D):
                g4_transform = transform
            else:
                g4_transform = g4.G4Transform3D(transform)
        return g4.G4PVPlacement(
            g4_transform,
            self.g4_logical_volume,  # logical volume
            volume_name,  # volume name
            self.mother_g4_logical_volume,  # mother volume or None if World
            False,  # no boolean operation # FIXME for BooleanVolume ?
            copy_index,  # copy number
            self.volume_engine.simulation_engine.simulation.user_info.check_volumes_overlap,
        )  # overlaps checking


class RepeatableVolume(VolumeBase):
    user_info_defaults = {
        "repeat": (
            None,
            {
                "setter_hook": _setter_hook_repeat,
                "doc": "A list of dictionaries, where each dictionary contains the parameters"
                "'name', 'translation', and 'rotation' for the respective repeated placement of the volume. ",
            },
        )
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # repeat might be passed as part of kwargs and be set via the super class
        # check compatibility with other user infos
        if self.repeat and (self.translation is not None or self.rotation is not None):
            fatal(
                f'When using "repeat", translation and rotation must be None, '
                f"for volume : {self.name}"
            )

    def construct_physical_volume(self):
        if self.repeat:
            self.construct_physical_volume_repeat()
        else:
            super().construct_physical_volume()
            # self.g4_physical_volumes.append(self._make_physical_volume(self.name))

    def construct_physical_volume_repeat(self):
        for i, repeat_params in enumerate(self.repeat):
            self.g4_physical_volumes.append(
                self._make_physical_volume(
                    repeat_params.name,
                    copy_index=i,
                    transform=get_g4_transform(
                        translation=repeat_params.translation,
                        rotation=repeat_params.rotation,
                    ),
                )
            )


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

    type_name = "RepeatParametrised"

    def __init__(self, repeated_volume, *args, **kwargs):
        self.repeated_volume = repeated_volume
        if "name" not in kwargs:
            kwargs["name"] = f"{repeated_volume.name}_param"
        kwargs["mother"] = repeated_volume.mother
        super().__init__(*args, **kwargs)
        if repeated_volume.build_physical_volume is True:
            warning(
                f"The repeated volume {repeated_volume.name} must have the "
                "'build_physical_volume' option set to False. "
                "Setting it to False."
            )
            repeated_volume.build_physical_volume = False
        self.repeat_parametrisation = None

    def close(self):
        self.repeated_volume.close()
        super().close()

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
                self.repeat_parametrisation,
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
        p = {}
        for k in keys:
            p[k] = self.user_info[k]
        self.repeat_parametrisation = g4.GateRepeatParameterisation()
        self.repeat_parametrisation.SetUserInfo(p)


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
            {"doc": "Path to the image file", "is_input_file": True},
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
    @property
    def size_pix(self):
        return np.array(itk.size(self.itk_image)).astype(int)

    # @requires_fatal('itk_image')
    @property
    def spacing(self):
        return np.array(self.itk_image.GetSpacing())

    @requires_fatal("volume_engine")
    def construct(self):
        # read image
        self.itk_image = itk.imread(check_filename_type(self.image))

        # shorter coding
        self.half_size_mm = self.size_pix * self.spacing / 2.0
        self.half_spacing = self.spacing / 2.0

        self.construct_material()
        self.construct_solid()
        self.construct_logical_volume()
        # create self.g4_voxel_param
        self.initialize_image_parameterisation()  # requires self.g4_logical_volume to be set before
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

        # # consider the 3D transform -> helpers_transform.
        # self.g4_physical_volumes.append(
        #     g4.G4PVPlacement(
        #         self.g4_transform,
        #         self.g4_logical_volume,  # logical volume
        #         self.name,  # volume name
        #         self.mother_g4_logical_volume,  # mother volume or None if World
        #         False,  # no boolean operation
        #         0,  # copy number
        #         True,
        #     )
        # )

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

    @requires_fatal("itk_image")
    @requires_fatal("volume_manager")
    def initialize_image_parameterisation(self):
        """
        From the input image, a label image is computed with each label
        associated with a material.
        The label image is initialized with label 0, corresponding to the first material
        Correspondence from voxel value to material is given by a list of interval [min_value, max_value, material_name]
        all pixels with values between min (included) and max (not included)
        will be associated with the given material
        """

        # prepare a LUT from material name to label
        self.material_to_label_lut = {}
        self.material_to_label_lut[self.material] = 0  # initialize with label 0

        # sort voxel_materials according to lower bounds
        sort_index = np.argsort([row[0] for row in self.voxel_materials])
        voxel_materials_sorted = [self.voxel_materials[i] for i in sort_index]

        # fill the LUT
        i = 1
        for row in voxel_materials_sorted:
            if row[2] not in self.material_to_label_lut:
                self.material_to_label_lut[row[2]] = i
                i += 1

        # make sure the materials are created in Geant4
        for m in self.material_to_label_lut:
            self.volume_manager.find_or_build_material(m)

        # create label image with same size as input image
        size_pix = np.array(itk.size(self.itk_image)).astype(int)
        spacing = np.array(self.itk_image.GetSpacing())
        self.label_image = create_3d_image(
            size_pix, spacing, pixel_type="unsigned short", fill_value=0
        )

        # get numpy array view of input and output itk images
        input = itk.array_view_from_image(self.itk_image)
        output = itk.array_view_from_image(self.label_image)

        # assign labels to output image
        # feed the material name through the LUT to get the label
        for row in self.voxel_materials:
            output[
                (input >= float(row[0])) & (input < float(row[1]))
            ] = self.material_to_label_lut[row[2]]

        # dump label image ?
        # FIXME: dump also LUT
        if self.dump_label_image:
            self.label_image.SetOrigin(
                self.itk_image.GetOrigin()
            )  # set origin as in input
            itk.imwrite(self.label_image, str(self.dump_label_image))

        # compute image origin such that it is centered at 0
        orig = -(size_pix * spacing) / 2.0 + spacing / 2.0
        self.label_image.SetOrigin(orig)

        # initialize parametrisation
        self.g4_voxel_param = g4.GateImageNestedParameterisation()

        # send image to cpp size
        update_image_py_to_cpp(
            self.label_image, self.g4_voxel_param.cpp_edep_image, True
        )
        self.g4_voxel_param.initialize_image()
        self.g4_voxel_param.initialize_material(list(self.material_to_label_lut.keys()))


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

    def close(self):
        pass


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
