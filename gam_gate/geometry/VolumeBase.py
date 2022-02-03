import gam_g4 as g4
from ..UserElement import *
from scipy.spatial.transform import Rotation
from box import BoxList
import time


class VolumeBase(UserElement):
    """
        Store information about a geometry volume:
        - G4 objects: Solid, LogicalVolume, PhysicalVolume
        - user parameters: user_info
        - additional data such as: mother, material etc
    """

    @staticmethod
    def set_default_user_info(user_info):
        gam.UserElement.set_default_user_info(user_info)
        user_info.mother = gam.__world_name__
        user_info.material = 'G4_AIR'
        user_info.translation = [0, 0, 0]
        user_info.color = [1, 1, 1, 1]
        user_info.rotation = Rotation.identity().as_matrix()
        user_info.repeat = None
        user_info.build_physical_volume = True

    def __init__(self, user_info):
        super().__init__(user_info)
        # convert the list of repeat to a BoxList to easier access
        self.user_info.repeat = BoxList(self.user_info.repeat)
        # init
        self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        # one volume may have several physical volume, this is the first one:
        self.g4_physical_volume = None
        # this list is all volumes (including first)
        self.g4_physical_volumes = []
        self.material = None
        self.g4_region = None
        # used
        self.volume_manager = None

    def __del__(self):
        pass

    def __str__(self):
        s = f'Volume: {self.user_info}'
        return s

    def build_solid(self):
        gam.fatal(f'Need to overwrite "build_solid" in {self.user_info}')

    def construct(self, volume_manager):
        self.volume_manager = volume_manager
        # check placements
        ui = self.user_info
        if ui.repeat:
            if ui.translation or ui.rotation:
                gam.fatal(f'When using "repeat", translation and rotation must be None, '
                          f'for volume : {ui.name}')
        # construct solid/material/lv/pv/regions
        self.construct_solid()
        self.construct_material()
        self.construct_logical_volume()
        if self.user_info.build_physical_volume:
            self.construct_physical_volume()
        self.construct_region()

    def construct_solid(self):
        # builder the G4 solid
        self.g4_solid = self.build_solid()
        # build the solid according to the type
        # self.g4_solid = self.solid_builder.Build(self.user_info)

    def construct_material(self):
        # retrieve or build the material
        self.material = self.volume_manager.find_or_build_material(self.user_info.material)

    def construct_logical_volume(self):
        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid,  # solid
                                                    self.material,  # material
                                                    self.user_info.name)  # name
        # color # FIXME to put elsewhere in a function
        self.g4_vis_attributes = g4.G4VisAttributes()
        self.g4_vis_attributes.SetColor(*self.user_info.color)
        if self.user_info.color[3] == 0:
            self.g4_vis_attributes.SetVisibility(False)
        else:
            self.g4_vis_attributes.SetVisibility(True)
        self.g4_logical_volume.SetVisAttributes(self.g4_vis_attributes)

    def construct_physical_volume(self):
        # find the mother's logical volume
        if self.user_info.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(self.user_info.mother, False)
        else:
            # fixme Check if world ?
            mother_logical = None
        # consider the 3D transform -> helpers_transform.
        if self.user_info.repeat:
            self.construct_physical_volume_repeat(mother_logical)
        else:
            transform = gam.get_vol_g4_transform(self.user_info)
            check = self.volume_manager.simulation.user_info.check_volumes_overlap
            self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                       self.g4_logical_volume,  # logical volume
                                                       self.user_info.name,  # volume name
                                                       mother_logical,  # mother volume or None if World
                                                       False,  # no boolean operation # FIXME for BooleanVolume ?
                                                       0,  # copy number
                                                       check)  # overlaps checking
            self.g4_physical_volumes.append(self.g4_physical_volume)

    def construct_physical_volume_repeat(self, mother_logical):
        check = self.volume_manager.simulation.user_info.check_volumes_overlap
        i = 0
        for repeat_vol in self.user_info.repeat:
            transform = gam.get_vol_g4_transform(repeat_vol)
            v = g4.G4PVPlacement(transform,
                                 self.g4_logical_volume,  # logical volume
                                 repeat_vol.name,  # volume name
                                 mother_logical,  # mother volume or None if World
                                 False,  # no boolean operation
                                 i,  # copy number
                                 check)  # overlaps checking
            i += 1
            self.g4_physical_volumes.append(v)
        self.g4_physical_volume = self.g4_physical_volumes[0]

    def construct_region(self):
        if self.user_info.name == gam.__world_name__:
            # the default region for the world is set by G4 RunManagerKernel
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
