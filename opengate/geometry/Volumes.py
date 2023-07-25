import numpy as np
import itk
from box import Box, BoxList
from anytree import NodeMixin
from scipy.spatial.transform import Rotation

import opengate_core as g4

from ..GateObjects import GateObject
from . import Solids
from ..helpers import fatal, warning, check_filename_type
from ..helpers_image import create_3d_image, update_image_py_to_cpp
from .helpers_transform import vec_np_as_g4, rot_np_as_g4, get_g4_transform
from ..Decorators import requires_warning, requires_fatal


""" Global name for the world volume"""
__world_name__ = "world"


def _check_user_info_rotation(rotation):
    """Internal function associated with user_info rotation to check its validity."""
    if rotation is None:
        return Rotation.identity().as_matrix()
    if not isinstance(rotation, (np.matrix, np.ndarray)) or rotation.shape != (3, 3):
        fatal("The user info 'rotation' should be a 3x3 array or matrix.")


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


# inherit from NodeMixin to turn the class into a tree node
class VolumeBase(GateObject, NodeMixin):
    """
    Store information about a geometry volume:
    - G4 objects: Solid, LogicalVolume, PhysicalVolume
    - user parameters: user_info
    - additional data such as: mother, material etc
    """

    user_info_defaults = {}
    user_info_defaults["mother"] = (
        __world_name__,
        {
            "doc": "Name of the mother volume.",
            "setter_hook": _setter_hook_user_info_mother,
        },
    )
    user_info_defaults["material"] = ("G4_AIR", {"doc": "Name of the material"})
    user_info_defaults["translation"] = (
        [0, 0, 0],
        {"doc": "3 component vector defining the translation w.r.t. the mother."},
    )
    user_info_defaults["color"] = (
        [1, 1, 1, 1],
        {
            "doc": (
                "4 component vector defining the volume's color in visual rendering. "
                "The first 3 entries are RBG, the 4th is visible/invisible (1 or 0). "
            )
        },
    )
    user_info_defaults["rotation"] = (
        Rotation.identity().as_matrix(),
        {
            "doc": "3x3 rotation matrix. Should be np.array or np.matrix.",
            "check_func": _check_user_info_rotation,
        },
    )
    user_info_defaults["build_physical_volume"] = (
        True,
        {
            "doc": "Boolean flag (True/False) whether G4 should build a physical volume.",
            "type": bool,
        },
    )

    def __init__(self, *args, **kwargs):
        try:
            self.volume_manager = kwargs["volume_manager"]
        except KeyError:
            self.volume_manager = None

        # GateObject base class digests all user info provided as kwargs
        super().__init__(*args, **kwargs)

        if self.mother is None:
            self.mother = __world_name__

        # if a template volume is provided, copy all user infos from it
        # except for the name of course
        if "template" in kwargs:
            for k, v in kwargs["template"].user_info.items():
                if k != "name":
                    self.user_info[k] = v

        # this attribute is used internally for the volumes tree
        # do not set it manually!
        self.parent = None

        # G4 references
        self.g4_world_log_vol = None
        self.g4_logical_volume = None
        self.g4_solid = None
        self.g4_vis_attributes = None
        # this list contains all physical volumes (in case of repeated volume)
        self.g4_physical_volumes = []
        self.g4_material = None

        # Allow user to create a volume without associating it to a simulation/manager
        # but issue a warning to make the user aware
        self.volume_engine = None

    def close(self):
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        self.g4_physical_volumes = []
        self.g4_material = None

    def _update_node(self):
        """Internal method which retrieves the volume object
        from the volume manager based on the mother's name stored as user info 'mother'
        """
        try:
            self.parent = self.volume_manager.volumes[self.mother]
        except KeyError:
            fatal(
                "Error while trying to update a volume tree node: \n"
                f"Mother volume of {self.name} should be {self.mother}, but it cannot be found in the list of volumes in the volume manager."
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
        return len(self.ancestors)

    @property
    @requires_warning("g4_logical_volume")
    def g4_region(self):
        if self.g4_logical_volume is None:
            return None
        else:
            return self.g4_logical_volume.GetRegion()

    # shortcut to first physical volume
    @property
    def g4_physical_volume(self):
        return self.g4_physical_volumes[0]

    # shortcuts to G4 variants of user infos translation and rotation
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

    @requires_fatal("volume_manager")
    def construct_material(self):
        # retrieve or build the material
        if self.material is None:
            self.g4_material = None
        else:
            self.g4_material = self.volume_manager.find_or_build_material(self.material)

    def construct(self):
        fatal(
            f"construct() method cannot be called on the base class {type(self).__name__}, only on inherited specific class. "
        )


class BooleanVolume(VolumeBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator_volume_1 = None
        self.creator_volume_2 = None

    def close(self):
        if self.creator_volume_1 is not None:
            self.creator_volume_1.close()
        if self.creator_volume_2 is not None:
            self.creator_volume_2.close()
        super().close()

    def intersect_with(
        self, other_volume, translation=None, rotation=None, new_name=None
    ):
        return self._perform_operation(
            "intersect",
            other_volume,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def add_to(self, other_volume, translation=None, rotation=None, new_name=None):
        return self._perform_operation(
            "add",
            other_volume,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def substract_from(
        self, other_volume, translation=None, rotation=None, new_name=None
    ):
        return self._perform_operation(
            "subtract",
            other_volume,
            translation=translation,
            rotation=rotation,
            new_name=new_name,
        )

    def _perform_operation(
        self, operation, other_volume, translation=None, rotation=None, new_name=None
    ):
        if rotation is None:
            rotation = Rotation.identity().as_matrix()
        if translation is None:
            translation = [0, 0, 0]

        if other_volume.g4_solid is None:
            other_volume.build_solid()
        if self.g4_solid is None:
            self.build_solid()
        if operation == "intersect":
            new_g4_solid = g4.G4IntersectionSolid(
                new_name, other_volume.g4_solid, self.g4_solid, rotation, translation
            )
            name_joiner = "times"
        elif operation == "add":
            new_g4_solid = g4.G4UnionSolid(
                new_name, other_volume.g4_solid, self.g4_solid, rotation, translation
            )
            name_joiner = "plus"
        elif operation == "subtract":
            new_g4_solid = g4.G4SubtractionSolid(
                new_name, other_volume.g4_solid, self.g4_solid, rotation, translation
            )
            name_joiner = "minus"
        else:
            fatal("Unknown boolean operation.")

        if new_name is None:
            new_name = f"({other_volume.name}_{name_joiner}_{self.name})"
        new_volume = BooleanVolume(name=new_name, template=other_volume)
        new_volume.g4_solid = new_g4_solid
        new_volume.creator_volume_1 = other_volume
        new_volume.creator_volume_2 = self
        return new_volume


class CSGVolumeBase(BooleanVolume):
    """Base class for Constructed Solid Geometry (CSG) Volumes.

    These are volumes whose shape (G4Solid) is defined mathematically based on a set of parameters.
    CSG Volumes can be combined via boolean operations, e.g. intersection, union, substraction.
    """

    user_info_defaults = {}

    user_info_defaults["repeat"] = (
        None,
        {
            "setter_hook": _setter_hook_repeat,
            "doc": "A list of dictionaries, where each dictionary contains the parameters"
            "'name', 'translation', and 'rotation' for the respective repeated placement of the volume. ",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # repeat might be passed as part of kwargs and be set via the super class
        if self.repeat:
            if self.translation is not None or self.rotation is not None:
                fatal(
                    f'When using "repeat", translation and rotation must be None, '
                    f"for volume : {self.name}"
                )

    def close(self):
        # all G4 references are defined in base class
        # nothing specific do to in the derived class
        super().close()

    def construct(self):
        self.construct_solid()
        self.construct_material()
        self.construct_logical_volume()
        if self.build_physical_volume is True:
            self.construct_physical_volume()

    # The construct_solid method is implemented here, but will only work with objects
    # of the derived classes which implement the build_solid method
    # The user receives a meaningful error.
    def construct_solid(self):
        try:
            self.g4_solid = self.build_solid()
        except AttributeError:
            fatal(
                f"You are trying to construct an object created from the base class {type(self).__name__}, "
                "but only specific CSG volumes, e.g. BoxVolume, can be constructed. "
            )

    @requires_fatal("g4_solid")
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
        if self.repeat:
            self.construct_physical_volume_repeat()
        else:
            self.g4_physical_volumes.append(self._build_physical_volume(self.name))

    def construct_physical_volume_repeat(self):
        for i, repeat_params in enumerate(self.repeat):
            self.g4_physical_volumes.append(
                self._build_physical_volume(
                    repeat_params.name,
                    copy_index=i,
                    transform=get_g4_transform(
                        translation=repeat_params.translation,
                        rotation=repeat_params.rotation,
                    ),
                )
            )

    @requires_fatal("volume_engine")
    def _build_physical_volume(self, volume_name, copy_index=0, transform=None):
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


# **** Specific CSG volumes ****
# They are defined by inheriting from the corresponding solid class
# Nothing else needs to be implemented here.


class BoxVolume(CSGVolumeBase, Solids.BoxSolid):
    """Volume with a box shape."""


class HexagonVolume(CSGVolumeBase, Solids.HexagonSolid):
    """Volume with a hexagon shape."""


class ConsVolume(CSGVolumeBase, Solids.ConsSolid):
    """Volume with a the shape of a cone or conical section."""


class PolyhedraVolume(CSGVolumeBase, Solids.PolyhedraSolid):
    """Volume with a polyhedral shape."""


class SphereVolume(CSGVolumeBase, Solids.SphereSolid):
    """Volume with a sphere or spherical shell shape."""


class TrapVolume(CSGVolumeBase, Solids.TrapSolid):
    """Volume with a generic trapezoidal shape."""


class TrdVolume(CSGVolumeBase, Solids.TrdSolid):
    """Volume with a symmetric trapezoidal shape."""


class TubsVolume(CSGVolumeBase, Solids.TubsSolid):
    """Volume with a tube or cylindrical section shape."""


class RepeatParametrisedVolume(VolumeBase):
    """
    Allow to repeat a volume with translations
    """

    user_info_defaults = {}
    user_info_defaults["linear_repeat"] = (
        None,
        {"required": True},
    )
    user_info_defaults["offset"] = (
        [0, 0, 0],
        {"doc": "3 component vector or list."},
    )
    user_info_defaults["start"] = ("auto", {})
    user_info_defaults["offset_nb"] = (1, {})

    type_name = "RepeatParametrised"

    def __init__(self, repeated_volume, *args, **kwargs):
        if not "name" in kwargs:
            kwargs["name"] = f"{repeated_volume.name}_param"
        super().__init__(*args, **kwargs)
        if repeated_volume.build_physical_volume is True:
            gate.warning(
                f"The repeated volume {repeated_volume.name} must have the "
                "'build_physical_volume' option set to False."
                "Setting it to False."
            )
            repeated_volume.build_physical_volume = False
        self.repeated_volume = repeated_volume
        if self.start is None:
            self.start = [
                -(x - 1) * y / 2.0 for x, y in zip(self.linear_repeat, self.translation)
            ]
        self.repeat_parametrisation = None

    def close(self):
        self.repeated_volume.close()
        super().close()

    def construct(self):
        # construct the repeated volume, incl. solid and log vol
        # but not the phys volume because that was disabled in init()
        self.repeated_volume.construct()
        self.construct_physical_volume()

    def create_repeat_parametrisation(self):
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

    def construct_physical_volume(self):
        # check if the mother is the world
        if self.mother_g4_logical_volume is None:
            fatal(f"The mother of {self.name} cannot be the world.")

        self.create_repeat_parametrisation()

        # number of copies
        n = (
            self.repeat_parametrisation.linear_repeat[0]
            * self.repeat_parametrisation.linear_repeat[1]
            * self.repeat_parametrisation.linear_repeat[2]
            * self.repeat_parametrisation.offset_nb
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
                False,
            )
        )


class ImageVolume(VolumeBase):
    """
    Store information about a voxelized volume
    """

    user_info_defaults = {}
    user_info_defaults["voxel_materials"] = (
        [[-np.inf, np.inf, "G4_AIR"]],
        {"doc": "FIXME"},
    )
    user_info_defaults["image"] = (
        "",
        {"doc": "Path to the image file"},
    )
    user_info_defaults["dump_label_image"] = (
        None,
        {
            "doc": "Path at which the image containing material labels should be saved. Set to None to dump no image."
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # look up table MATERIAL -> LABEL
        self.material_to_label_lut = None

        # ITK images
        self.itk_image = None  # the input
        self.label_image = None  # image storing material labels

        # G4 references (additionally to those in base class)
        self.reset_g4_references()

    def close(self):
        self.reset_g4_references()
        super().close()

    def reset_g4_references(self):
        self.g4_physical_z = None
        self.g4_logical_z = None
        self.g4_solid_z = None
        self.g4_physical_x = None
        self.g4_logical_x = None
        self.g4_solid_x = None
        self.g4_physical_y = None
        self.g4_logical_y = None
        self.g4_solid_y = None
        self.g4_voxel_param = None

    @requires_fatal("volume_engine")
    def construct(self):
        # read image
        self.itk_image = itk.imread(check_filename_type(self.image))
        # extract properties
        size_pix = np.array(itk.size(self.itk_image)).astype(int)
        spacing = np.array(self.itk_image.GetSpacing())
        size_mm = size_pix * spacing

        # shorter coding
        half_size_mm = size_mm / 2.0
        half_spacing = spacing / 2.0

        # build the bounding box volume
        self.g4_solid = g4.G4Box(
            self.name, half_size_mm[0], half_size_mm[1], half_size_mm[2]
        )
        self.construct_material()
        self.g4_logical_volume = g4.G4LogicalVolume(
            self.g4_solid, self.g4_material, self.name
        )

        # param Y
        self.g4_solid_y = g4.G4Box(
            self.name + "_Y", half_size_mm[0], half_spacing[1], half_size_mm[2]
        )
        self.g4_logical_y = g4.G4LogicalVolume(
            self.g4_solid_y, self.g4_material, self.name + "_log_Y"
        )
        self.g4_physical_y = g4.G4PVReplica(
            self.name + "_Y",
            self.g4_logical_y,
            self.g4_logical_volume,
            g4.EAxis.kYAxis,
            size_pix[1],  # nReplicas
            spacing[1],  # width
            0.0,
        )  # offset

        # param X
        self.g4_solid_x = g4.G4Box(
            self.name + "_X", half_spacing[0], half_spacing[1], half_size_mm[2]
        )
        self.g4_logical_x = g4.G4LogicalVolume(
            self.g4_solid_x, self.g4_material, self.name + "_log_X"
        )
        self.g4_physical_x = g4.G4PVReplica(
            self.name + "_X",
            self.g4_logical_x,
            self.g4_logical_y,
            g4.EAxis.kXAxis,
            size_pix[0],
            spacing[0],
            0.0,
        )

        # param Z
        self.g4_solid_z = g4.G4Box(
            self.name + "_Z", half_spacing[0], half_spacing[1], half_spacing[2]
        )
        self.g4_logical_z = g4.G4LogicalVolume(
            self.g4_solid_z, self.g4_material, self.name + "_log_Z"
        )

        # this creates self.g4_voxel_param
        # requires self.g4_logical_volume to be set before
        self.initialize_image_parameterisation()

        self.g4_physical_z = g4.G4PVParameterised(
            self.name + "_Z",
            self.g4_logical_z,
            self.g4_logical_x,
            g4.EAxis.kZAxis,  # g4.EAxis.kUndefined, ## FIXME ?
            size_pix[2],
            self.g4_voxel_param,
            False,
        )  # overlaps checking

        # consider the 3D transform -> helpers_transform.
        self.g4_physical_volumes.append(
            g4.G4PVPlacement(
                self.g4_transform,
                self.g4_logical_volume,  # logical volume
                self.name,  # volume name
                self.mother_g4_logical_volume,  # mother volume or None if World
                False,  # no boolean operation
                0,  # copy number
                True,
            )
        )
        # self.volume_manager.simulation.physics_manager.create_region(self.name)

    @requires_fatal("itk_image")
    @requires_fatal("volume_manager")
    def initialize_image_parameterisation(self):
        """
        From the input image, a label image is computed with each label
        associated with a material.
        The label image is initialized with label 0, corresponding to the first material
        Correspondence from voxel value to material is given by a list of interval [min_value, max_value, material_name]
        all pixels with values between min (included) and max (non included)
        will be associated with the given material
        """

        # FIXME: make setter hook to guarantee np.array
        voxel_materials = np.asarray(self.voxel_materials)  # becomes dtype='<U32'
        # sort by first column (inferior binning limit)
        voxel_materials_sorted = voxel_materials[
            voxel_materials[:, 0].astype(float).argsort()
        ]

        # prepare a LUT from material name to label
        self.material_to_label_lut = {}
        self.material_to_label_lut[self.material] = 0  # initialize with label 0
        # fill the LUT
        i = 1
        for m in voxel_materials_sorted[:, 2]:
            if m not in self.material_to_label_lut:
                self.material_to_label_lut[m] = i
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
        for row in voxel_materials_sorted:
            output[
                (input >= float(row[0])) & (input < float(row[1]))
            ] = self.material_to_label_lut[row[2]]

        # dump label image ?
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
    def __init__(self, name, volume_manager, *args, **kwargs):
        super().__init__()
        self.name = name
        self.parent = self.volume_manager.volume_tree_root

        self.volume_manager = volume_manager
        self.parallel_world_engine = None

        self.reset_g4_references()

    def reset_g4_references(self):
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

    def close(self):
        self.reset_g4_references()

    @requires_fatal("parallel_world_engine")
    def construct(self):
        # get the physical volume through the parallel world engine
        # do not construct it
        self.g4_world_phys_vol = self.parallel_world_engine.GetWorld()
        self.g4_world_log_vol = self.g4_world_phys_vol.GetLogicalVolume()
