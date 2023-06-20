import numpy as np
import itk
from box import Box

import opengate_core as g4
from ..UserElement import *
from scipy.spatial.transform import Rotation
from box import BoxList

from opengate.helpers_log import log
from ..helpers import fatal, warning
from ..helpers_image import create_3d_image, update_image_py_to_cpp
from .helpers_transform import vec_np_as_g4, rot_np_as_g4, get_g4_transform
from ..Decorators import requires_warning, requires_fatal
from . import Solids

from opengate.GateObjects import GateObject
from opengate.geometry.Solids import SolidBase


def _check_user_info_rotation(rotation):
    """Internal function associated with user_info rotation to check its validity."""
    if rotation is None:
        return Rotation.identity().as_matrix()
    if not isinstance(rotation, (np.matrix, np.ndarray)) or rotation.shape != (3, 3):
        fatal("The user info 'rotation' should be a 3x3 array or matrix.")


class GateVolume(GateObject):
    """
    Store information about a geometry volume:
    - G4 objects: Solid, LogicalVolume, PhysicalVolume
    - user parameters: user_info
    - additional data such as: mother, material etc
    """

    user_info_defaults = {}
    user_info_defaults["mother"] = (
        gate.__world_name__,
        {"doc": "Name of the mother volume."},
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
    user_info_defaults["repeat"] = (None, {})
    user_info_defaults["build_physical_volume"] = (
        True,
        {
            "doc": "Boolean flag (True/False) whether G4 should build a physical volume.",
            "type": bool,
        },
    )
    user_info_defaults["volume_type"] = (
        True,
        {
            "doc": "The type of volume which defines the type of solid (shape).",
        },
    )

    solid_classes = {}
    solid_classes["Box"] = Solids.BoxSolid
    solid_classes["Hexagon"] = Solids.HexagonSolid
    solid_classes["Cons"] = Solids.ConsSolid
    solid_classes["Polyhedra"] = Solids.PolyhedraSolid
    solid_classes["Sphere"] = Solids.SphereSolid
    solid_classes["Trap"] = Solids.TrapSolid
    solid_classes["Trd"] = Solids.TrdSolid
    solid_classes["Tubs"] = Solids.TubsSolid

    def __init__(self, volume_manager, volume_type=None, solid=None, *args, **kwargs):
        if volume_type is None and solid is None:
            fatal(
                "You must provide either a volume_type or an existing solid when creating a volume."
            )
        if volume_type is not None and solid is not None:
            fatal(
                "You can provide either a volume_type or an existing solid when creating a volume. Not both."
            )
        # create solid based on desired volume type
        if volume_type is not None:
            # get the solid class corresponding to the volume type
            try:
                solid_class = self.solid_classes[volume_type]
            except KeyError:
                try:
                    # User might have provided name in format xxxVolume
                    solid_class = self.solid_classes[volume_type.rstrip("Volume")]
                except KeyError:
                    fatal(f"Unknown volume type {volume_type}.")
            # grab user_infos for solid from kwargs
            user_info_solid = {}
            for k in solid_class.inherited_user_info_defaults.keys():
                try:
                    user_info_solid[k] = kwargs[k]
                except KeyError:
                    continue
            self.solid = solid_class(*args, **user_info_solid)
        # solid object provided
        else:
            if solid._part_of_volume is not None:
                fatal(f"The solid {solid.name} is already part of a volume.")
            self.solid = solid
            # pick name from solid, if none is provided explicitly
            if "name" not in kwargs.keys():
                kwargs["name"] = solid.name + "_volume"
        self.solid._part_of_volume = self.name

        super().__init__(*args, **kwargs)

        if self.repeat:
            if self.translation is not None or self.rotation is not None:
                gate.fatal(
                    f'When using "repeat", translation and rotation must be None, '
                    f"for volume : {self.name}"
                )

        # convert the list of repeat to a BoxList to easier access
        self.user_info["repeat"] = BoxList(self.user_info["repeat"])
        if self.mother is None:
            self.mother = gate.__world_name__

        # G4 references
        self.g4_world_log_vol = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        # this list contains all volumes (including first)
        self.g4_physical_volumes = []
        self.g4_material = None

        # Allow user to create a volume without associating it to a simulation/manager
        # but issue a warning to make the user aware
        if volume_manager is None:
            warning(
                "Volume created without a physics manager. Some functions will not work. "
            )
        self.volume_manager = volume_manager
        self.volume_engine = None

    def close(self):
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_world_log_vol = None
        # self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        self.g4_physical_volumes = []
        self.g4_material = None

    def __str__(self):
        s = f"Volume: {self.user_info}"
        return s

    @property
    def g4_solid(self):
        return self.solid.g4_solid

    @property
    @requires_warning("g4_logical_volume")
    def g4_region(self):
        if self.g4_logical_volume is None:
            return None
        else:
            return self.g4_logical_volume.GetRegion()

    @property
    def g4_physical_volume(self):
        return self.g4_physical_volumes[0]

    @property
    def g4_translation(self):
        return vec_np_as_g4(self.translation)

    @property
    def g4_rotation(self):
        return rot_np_as_g4(self.rotation)

    @property
    def g4_transform(self):
        return get_g4_transform(self.translation, self.rotation)

    def construct(self, g4_world_log_vol):
        self.g4_world_log_vol = g4_world_log_vol
        # construct solid/material/lv/pv/regions
        self.construct_solid()
        self.construct_material()
        self.construct_logical_volume()
        if self.user_info.build_physical_volume is True:
            self.construct_physical_volume()

    def construct_solid(self):
        # build solid if necessary
        # it might have been constructed before, e.g. from boolean operation
        if self.solid.g4_solid is None:
            self.solid.build_solid()

    @requires_fatal("volume_engine")
    def construct_material(self):
        # retrieve or build the material
        if self.material is None:
            self.g4_material = None
        else:
            self.g4_material = self.volume_engine.find_or_build_material(self.material)

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

    @property
    def mother_g4_logical_volume(self):
        if self.mother is gate.__world_name__:
            return None
        else:
            return g4.G4LogicalVolumeStore.GetInstance().GetVolume(self.mother, False)

    def _build_physical_volume(self, volume_name, copy_index=0, transform=None):
        if transform is None:
            if isinstance(transform, g4.G4Transform3D):
                g4_transform = transform
            else:
                g4_transform = g4.G4Transform3D(transform)
            transform = self.g4_transform
        return g4.G4PVPlacement(
            transform,
            self.g4_logical_volume,  # logical volume
            volume_name,  # volume name
            self.mother_g4_logical_volume,  # mother volume or None if World
            False,  # no boolean operation # FIXME for BooleanVolume ?
            copy_index,  # copy number
            self.volume_engine.simulation_engine.simulation.user_info.check_volumes_overlap,
        )  # overlaps checking

    def construct_physical_volume(self):
        if self.repeat:
            self.construct_physical_volume_repeat()
        else:
            self.g4_physical_volumes.append(self._build_physical_volume(self.name))

    def construct_physical_volume_repeat(self):
        for i, repeat_vol in enumerate(self.repeat):
            self.g4_physical_volumes.append(
                self._build_physical_volume(
                    repeat_vol.name,
                    copy_index=i,
                    transform=gate.get_vol_g4_transform(repeat_vol),
                )
            )


class RepeatParametrisedVolume(GateVolume):
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

    def construct_solid(self):
        # no solid to build
        pass

    def construct_logical_volume(self):
        # make sure the repeated volume's logical volume is constructed
        if self.repeated_volume.g4_logical_volume is None:
            self.repeated_volume.construct_logical_volume()
        # set log vol
        self.g4_logical_volume = self.repeated_volume.g4_logical_volume

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
        self.param = g4.GateRepeatParameterisation()
        self.param.SetUserInfo(p)

    def construct_physical_volume(self):
        # find the mother's logical volume
        st = g4.G4LogicalVolumeStore.GetInstance()
        g4_mother_logical_volume = st.GetVolume(self.mother, False)
        if not g4_mother_logical_volume:
            gate.fatal(f"The mother of {self.name} cannot be the world.")

        self.create_repeat_parametrisation()

        # number of copies
        n = (
            self.param.linear_repeat[0]
            * self.param.linear_repeat[1]
            * self.param.linear_repeat[2]
            * self.param.offset_nb
        )

        # (only daughter)
        # g4.EAxis.kUndefined => faster
        self.g4_physical_volumes.append(
            g4.G4PVParameterised(
                self.name,
                self.g4_logical_volume,
                g4_mother_logical_volume,
                g4.EAxis.kUndefined,
                n,
                self.param,
                False,
            )
        )


class ImageVolume(GateVolume):
    """
    Store information about a voxelized volume
    """

    user_info_defaults = {}
    user_info_defaults["voxel_materials"] = (
        [[-np.inf, np.inf, "G4_AIR"]],
        {"doc": "FIXME"},
    )
    user_info_defaults["dump_label_image"] = (
        None,
        {"doc": "FIXME"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # G4 references
        self.g4_solid_bounding_box = None
        self.g4_logical_volume_bounding_box = None
        self.g4_physical_z = None
        self.g4_logical_z = None
        self.g4_solid_z = None
        self.g4_physical_x = None
        self.g4_logical_x = None
        self.g4_solid_x = None
        self.g4_physical_y = None
        self.g4_logical_y = None
        self.g4_solid_y = None

        # ITK images
        self.itk_image = None  # the input
        self.label_image = None  # image storing material labels

    def close(self):
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_solid_bounding_box = None
        self.g4_logical_volume_bounding_box = None
        self.g4_physical_z = None
        self.g4_logical_z = None
        self.g4_solid_z = None
        self.g4_physical_x = None
        self.g4_logical_x = None
        self.g4_solid_x = None
        self.g4_physical_y = None
        self.g4_logical_y = None
        self.g4_solid_y = None

    @requires_fatal("volume_engine")
    def construct(self, volume_engine, g4_world_log_vol):
        self.volume_engine = volume_engine
        # read image
        self.itk_image = itk.imread(gate.check_filename_type(self.image))
        size_pix = np.array(itk.size(self.itk_image)).astype(int)
        spacing = np.array(self.itk_image.GetSpacing())
        size_mm = size_pix * spacing

        # shorter coding
        hsize_mm = size_mm / 2.0
        hspacing = spacing / 2.0

        # build the bounding box volume
        self.g4_solid_bounding_box = g4.G4Box(
            self.name, hsize_mm[0], hsize_mm[1], hsize_mm[2]
        )
        def_mat = volume_engine.find_or_build_material(self.material)
        self.g4_logical_volume_bounding_box = g4.G4LogicalVolume(
            self.g4_solid_bounding_box, def_mat, self.name
        )

        # param Y
        self.g4_solid_y = g4.G4Box(
            self.name + "_Y", hsize_mm[0], hspacing[1], hsize_mm[2]
        )
        self.g4_logical_y = g4.G4LogicalVolume(
            self.g4_solid_y, def_mat, self.name + "_log_Y"
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
            self.name + "_X", hspacing[0], hspacing[1], hsize_mm[2]
        )
        self.g4_logical_x = g4.G4LogicalVolume(
            self.g4_solid_x, def_mat, self.name + "_log_X"
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
            self.name + "_Z", hspacing[0], hspacing[1], hspacing[2]
        )
        self.g4_logical_z = g4.G4LogicalVolume(
            self.g4_solid_z, def_mat, self.name + "_log_Z"
        )
        self.initialize_image_parameterisation()  # this creates self.g4_voxel_param
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
        self.g4_physical_volume = g4.G4PVPlacement(
            self.g4_transform,
            self.g4_logical_volume,  # logical volume
            self.name,  # volume name
            self.mother_g4_logical_volume,  # mother volume or None if World
            False,  # no boolean operation
            0,  # copy number
            True,
        )  # overlaps checking

    @requires_fatal("itk_image")
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
        voxel_materials = np.asarray(self.voxel_materials)
        # sort by first column (inferior binning limit)
        voxel_materials_sorted = voxel_materials[voxel_materials[:, 0].argsort()]

        # prepare a LUT from material name to label
        material_to_label_lut = {}
        material_to_label_lut[self.material] = 0  # initialize with label 0
        # fill the LUT
        for i, m in enumerate(np.unique(voxel_materials_sorted[:, 2])):
            material_to_label_lut[m] = i + 1  # offset by one because 0 is already used

        # make sure the materials are created in Geant4
        for m in material_to_label_lut:
            self.volume_engine.find_or_build_material(m)

        # create label image with same size as input image
        size_pix = np.array(itk.size(self.itk_image)).astype(int)
        spacing = np.array(self.itk_image.GetSpacing())
        self.label_image = create_3d_image(
            size_pix, spacing, pixel_type="unsigned short", fill_value=0
        )

        # get numpy array view of input and output itk images
        output = itk.array_view_from_image(self.label_image)
        input = itk.array_view_from_image(self.itk_image)

        # assign labels to output image
        for row in voxel_materials_sorted:
            output[(input >= row[0]) & (input < row[1])] = material_to_label_lut[row[2]]

        # dump label image ?
        if self.dump_label_image:
            self.label_image.SetOrigin(
                self.itk_image.GetOrigin()
            )  # set origin as in input
            itk.imwrite(self.label_image, str(self.dump_label_image))

        # compute image origin such that it is centered at 0
        orig = -(size_pix * spacing) / 2.0 + spacing / 2.0
        self.label_image.SetOrigin(orig)

        # send image to cpp size
        update_image_py_to_cpp(
            self.label_image, self.g4_voxel_param.cpp_edep_image, True
        )

        # initialize parametrisation
        self.g4_voxel_param = g4.GateImageNestedParameterisation()
        self.g4_voxel_param.initialize_image()
        self.g4_voxel_param.initialize_material(list(self.material_to_label_lut.keys()))


# create classes for simple types of Volumes for convenience
def make_inherited_volume_class(volume_type):
    def init_method(self, volume_manager, *args, **kwargs):
        try:
            kwargs.pop("volume_type")
        except KeyError:
            pass
        try:
            kwargs.pop("solid")
        except KeyError:
            pass

        super(self).__init__(
            volume_manager, volume_type=volume_type, solid=None * args, **kwargs
        )

    volume_class_name = volume_type + "Volume"
    cls = type(
        volume_class_name,
        (GateVolume,),
        {
            "__init__": init_method,
        },
    )
    return cls


BoxVolume = make_inherited_volume_class("BoxVolume")
HexagonVolume = make_inherited_volume_class("HexagonVolume")
ConsVolume = make_inherited_volume_class("ConsVolume")
PolyhedraVolume = make_inherited_volume_class("PolyhedraVolume")
SphereVolume = make_inherited_volume_class("SphereVolume")
TrapVolume = make_inherited_volume_class("TrapVolume")
TrdVolume = make_inherited_volume_class("TrdVolume")
TubsVolume = make_inherited_volume_class("TubsVolume")
