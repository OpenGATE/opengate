import numpy as np
from box import Box

import opengate_core as g4
from ..UserElement import *
from scipy.spatial.transform import Rotation
from box import BoxList

from opengate.helpers_log import log
from opengate.helpers import fatal, warning
from opengate.geometry.helpers_transform import vec_np_as_g4, rot_np_as_g4
from opengate.Decorators import requires_warning, requires_fatal
from opengate.geometry import Solids

from opengate.GateObjects import GateObject
from opengate.geometry.Solids import SolidBase


def _check_user_info_rotation(rotation):
    """Internal function associated with user_info rotation to check its validity."""
    if rotation is None:
        return Rotation.identity().as_matrix()
    if not isinstance(rotation, (np.matrix, np.ndarray)) or rotation.shape != (3, 3):
        fatal("The user info 'rotation' should be a 3x3 array or matrix.")


class VolumeBase(GateObject):
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
    solid_classes["BoxSolid"] = Solids.BoxSolid
    solid_classes["HexagonSolid"] = Solids.HexagonSolid
    solid_classes["ConsSolid"] = Solids.ConsSolid
    solid_classes["PolyhedraSolid"] = Solids.PolyhedraSolid
    solid_classes["SphereSolid"] = Solids.SphereSolid
    solid_classes["TrapSolid"] = Solids.TrapSolid
    solid_classes["TrdSolid"] = Solids.TrdSolid
    solid_classes["TubsSolid"] = Solids.TubsSolid

    def __init__(self, volume_manager, volume_type=None, solid=None, *args, **kwargs):
        # if a solid is provided, grab the relevant user info from it.
        if volume_type is None and solid is None:
            fatal(
                "You must provide either a volume_type or an existing solid when creating a volume."
            )
        if volume_type is not None:
            # get the solid class corresponding to the volume type
            try:
                solid_class = self.solid_classes[volume_type]
            except KeyError:
                solid_name = volume_type.rstrip("Volume") + "Solid"
                try:
                    solid_class = self.solid_classes[solid_name]
                except KeyError:
                    fatal(f"Unknown volume type {volume_type}.")
            # at this point, we either have a valid solid class, or an exception
            # make sure the solid has not yet been used in another volume
            if solid is not None and solid._part_of_volume is not None:
                # check if solid and volume type are compatible
                if not isinstance(solid, solid_class):
                    fatal(
                        f"Volume type {volume_type} incompatible with provided solid type {type(solid).__name__}."
                    )
                # set solid to the provided solid
                self.solid = solid
            else:
                # no solid provided, so need to create one
                # extract user info for the solid if provided as keyword arguments here
                user_info_solid = {}
                for k in solid_class.inherited_user_info_defaults.keys():
                    try:
                        user_info_solid[k] = kwargs[k]
                    except KeyError:
                        continue
                self.solid = solid_class(*args, **user_info_solid)
        # no volume type provided, but a solid object
        # (otherwise an exception would have been raise above):
        else:
            # make sure the solid has not yet been used in another volume
            if solid._part_of_volume is not None:
                fatal(
                    f"The provided solid {solid.name} is already used in volume {solid._part_of_volume}."
                )
            self.solid = solid
            # allow user to use same name as solid automatically
            if "name" not in kwargs.keys():
                kwargs["name"] = solid.name
        self.solid._part_of_volume = self.name

        super().__init__(*args, **kwargs)

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
        return g4.G4Transform3D(self.g4_rotation, self.g4_translation)

    def construct(self, g4_world_log_vol):
        self.g4_world_log_vol = g4_world_log_vol
        # check placements
        ui = self.user_info
        if ui.repeat:
            if ui.translation is not None or ui.rotation is not None:
                gate.fatal(
                    f'When using "repeat", translation and rotation must be None, '
                    f"for volume : {ui.name}"
                )
        # construct solid/material/lv/pv/regions
        self.construct_solid()
        self.construct_material()
        self.construct_logical_volume()
        if self.user_info.build_physical_volume is True:
            self.construct_physical_volume()

    def construct_solid(self):
        # solid might have been constructed before, e.g. from boolean operation
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
        if self.user_info.repeat:
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
