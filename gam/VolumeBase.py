import gam_g4 as g4
from .ElementBase import *


class VolumeBase(ElementBase):
    """
        Store information about a geometry volume:
        - G4 objects: Solid, LogicalVolume, PhysicalVolume
        - user parameters: user_info
        - additional data such as: mother, material etc
    """

    def __init__(self, name):
        ElementBase.__init__(self, name)
        self.user_info.mother = 'World'
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

    def __del__(self):
        pass

    def __str__(self):
        s = f'Volume: {self.user_info}'
        return s

    def build_solid(self):
        gam.fatal(f'Need to overwrite "build_solid" in {self.user_info}')

    def construct(self, vol_manager):
        # builder the G4 solid
        self.g4_solid = self.build_solid()

        # build the solid according to the type
        # self.g4_solid = self.solid_builder.Build(self.user_info)

        # retrieve or build the material
        vol = self.user_info
        material = vol_manager.find_or_build_material(vol.material)

        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid,  # solid
                                                    material,  # material
                                                    vol.name)  # name
        # color
        self.g4_vis_attributes = g4.G4VisAttributes()
        self.g4_vis_attributes.SetColor(*self.user_info.color)
        self.g4_logical_volume.SetVisAttributes(self.g4_vis_attributes)

        # find the mother's logical volume
        if vol.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(vol.mother, False)
        else:
            mother_logical = None

        # consider the 3D transform -> helpers_transform.
        transform = gam.get_vol_g4_transform(vol)
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking
