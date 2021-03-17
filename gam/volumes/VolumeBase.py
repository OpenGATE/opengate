import gam_g4 as g4
from ..ElementBase import *
from gam.VolumeManager import __world_name__


class VolumeBase(ElementBase):
    """
        Store information about a geometry volume:
        - G4 objects: Solid, LogicalVolume, PhysicalVolume
        - user parameters: user_info
        - additional data such as: mother, material etc
    """

    def __init__(self, name):
        ElementBase.__init__(self, name)
        self.user_info.mother = __world_name__
        self.user_info.material = 'G4_AIR'
        self.user_info.translation = [0, 0, 0]
        self.user_info.color = [1, 1, 1, 1]
        from scipy.spatial.transform import Rotation
        self.user_info.rotation = Rotation.identity().as_matrix()
        # init
        self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_vis_attributes = None
        self.g4_physical_volume = None
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
        # check the user parameters
        self.check_user_info()
        # construct solid/material/lv/pv/regions
        self.construct_solid()
        self.construct_material()
        self.construct_logical_volume()
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
        # color
        self.g4_vis_attributes = g4.G4VisAttributes()
        self.g4_vis_attributes.SetColor(*self.user_info.color)
        self.g4_logical_volume.SetVisAttributes(self.g4_vis_attributes)

    def construct_physical_volume(self):
        # find the mother's logical volume
        if self.user_info.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(self.user_info.mother, False)
        else:
            mother_logical = None

        # consider the 3D transform -> helpers_transform.
        transform = gam.get_vol_g4_transform(self.user_info)
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   self.user_info.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation # FIXME for BooleanVolume ?
                                                   0,  # copy number
                                                   True)  # overlaps checking

    def construct_region(self):
        if self.user_info.name == __world_name__:
            # the default region for the world is set by G4 RunManagerKernel
            return
        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.user_info.name)
        self.g4_logical_volume.SetRegion(self.g4_region)
        self.g4_region.AddRootLogicalVolume(self.g4_logical_volume, True)
