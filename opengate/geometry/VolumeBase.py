from scipy.spatial.transform import Rotation
from box import BoxList

import opengate_core as g4
from ..userelement import UserElement
from ..decorators import requires_warning
from ..definitions import __world_name__
from .utility import get_vol_g4_transform
from ..utility import fatal


class VolumeBase(UserElement):
    """
    Store information about a geometry volume:
    - G4 objects: Solid, LogicalVolume, PhysicalVolume
    - user parameters: user_info
    - additional data such as: mother, material etc
    """

    element_type = "Volume"

    @staticmethod
    def set_default_user_info(user_info):
        UserElement.set_default_user_info(user_info)
        user_info.mother = __world_name__
        user_info.material = "G4_AIR"
        user_info.translation = [0, 0, 0]
        user_info.color = [1, 1, 1, 1]
        user_info.rotation = Rotation.identity().as_matrix()
        user_info.repeat = None
        user_info.build_physical_volume = True
        # not all volumes should automatically become regions
        # (see comment in construct method):
        # user_info.make_region = True

    def __init__(self, user_info):
        super().__init__(user_info)
        # convert the list of repeat to a BoxList to easier access
        self.user_info.repeat = BoxList(self.user_info.repeat)
        # init
        self.g4_world_log_vol = None
        self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        # one volume may have several physical volume, this is the first one:
        self.g4_physical_volume = None
        # this list contains all volumes (including first)
        self.g4_physical_volumes = []
        self.material = None
        # self.g4_region = None # turned into property
        # used
        self.volume_engine = None

    def __del__(self):
        pass

    def __str__(self):
        s = f"Volume: {self.user_info}"
        return s

    @property
    @requires_warning("g4_logical_volume")
    def g4_region(self):
        if self.g4_logical_volume is None:
            return None
        else:
            return self.g4_logical_volume.GetRegion()

    def build_solid(self):
        fatal(f'Need to overwrite "build_solid" in {self.user_info}')

    def construct(self, volume_engine, g4_world_log_vol):
        self.volume_engine = volume_engine
        self.g4_world_log_vol = g4_world_log_vol
        # check placements
        ui = self.user_info
        if ui.repeat:
            if ui.translation is not None or ui.rotation is not None:
                fatal(
                    f'When using "repeat", translation and rotation must be None, '
                    f"for volume : {ui.name}"
                )
        # construct solid/material/lv/pv/regions
        self.construct_solid()
        self.construct_material(volume_engine)
        self.construct_logical_volume()
        if self.user_info.build_physical_volume is True:
            self.construct_physical_volume()

    def construct_solid(self):
        # builder the G4 solid
        self.g4_solid = self.build_solid()
        # build the solid according to the type
        # self.g4_solid = self.solid_builder.Build(self.user_info)

    def construct_material(self, volume_engine):
        # retrieve or build the material
        if self.user_info.material is None:
            self.material = None
        else:
            self.material = volume_engine.find_or_build_material(
                self.user_info.material
            )

    def construct_logical_volume(self):
        self.g4_logical_volume = g4.G4LogicalVolume(
            self.g4_solid, self.material, self.user_info.name
        )
        # color
        self.g4_vis_attributes = g4.G4VisAttributes()
        self.g4_vis_attributes.SetColor(*self.user_info.color)
        if self.user_info.color[3] == 0:
            self.g4_vis_attributes.SetVisibility(False)
        else:
            self.g4_vis_attributes.SetVisibility(True)
        self.g4_logical_volume.SetVisAttributes(self.g4_vis_attributes)

    def get_mother_logical_volume(self):
        """
        Find the mother logical volume.
        If the mother's name is None, it is the (mass) world.
        """
        if self.user_info.mother is None:
            return None
        st = g4.G4LogicalVolumeStore.GetInstance()
        return st.GetVolume(self.user_info.mother, False)

    def construct_physical_volume(self):
        # find the mother's logical volume
        mother_logical = self.get_mother_logical_volume()
        # consider the 3D transform -> helpers_transform.
        if self.user_info.repeat:
            self.construct_physical_volume_repeat(mother_logical)
        else:
            transform = get_vol_g4_transform(self.user_info)
            check = (
                self.volume_engine.simulation_engine.simulation.user_info.check_volumes_overlap
            )
            self.g4_physical_volume = g4.G4PVPlacement(
                transform,
                self.g4_logical_volume,  # logical volume
                self.user_info.name,  # volume name
                mother_logical,  # mother volume or None if World
                False,  # no boolean operation # FIXME for BooleanVolume ?
                0,  # copy number
                check,
            )  # overlaps checking
            self.g4_physical_volumes.append(self.g4_physical_volume)

    def construct_physical_volume_repeat(self, mother_logical):
        check = (
            self.volume_engine.simulation_engine.simulation.user_info.check_volumes_overlap
        )
        i = 0
        for repeat_vol in self.user_info.repeat:
            transform = get_vol_g4_transform(repeat_vol)
            v = g4.G4PVPlacement(
                transform,
                self.g4_logical_volume,  # logical volume
                repeat_vol.name,  # volume name
                mother_logical,  # mother volume or None if World
                False,  # no boolean operation
                i,  # copy number
                check,
            )  # overlaps checking
            i += 1
            self.g4_physical_volumes.append(v)
        self.g4_physical_volume = self.g4_physical_volumes[0]

    def construct_region(self):
        if self.user_info.name == __world_name__:
            # the default region for the world is set by G4 RunManagerKernel
            return
        if (
            self.user_info.name
            in self.volume_engine.volume_manager.parallel_world_names
        ):
            # no regions for other worlds
            return
        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.user_info.name)
        # set a fake default production cuts to avoid warning
        # (warning in G4RunManagerKernel::CheckRegions())
        # keep it in self to avoid garbage collecting
        self.fake_cuts = g4.G4ProductionCuts()
        self.g4_region.SetProductionCuts(self.fake_cuts)
        # set region and Log Vol
        self.g4_logical_volume.SetRegion(self.g4_region)
        self.g4_region.AddRootLogicalVolume(self.g4_logical_volume, True)
