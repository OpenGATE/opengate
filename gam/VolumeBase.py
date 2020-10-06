import gam
import gam_g4 as g4


class VolumeBase:
    """
        Store information about a geometry volume:
        - G4 objects: Solid, LogicalVolume, PhysicalVolume
        - user parameters: user_info
        - additional data such as: mother, material etc
    """

    def __init__(self, volume_info):
        """
        FIXME
        """
        self.user_info = volume_info
        self.g4_solid = None
        self.g4_logical_volume = None
        self.g4_physical_volume = None
        self.g4_material = None
        self.solid_builder = gam.get_solid_builder(self.user_info.type)
        self.solid_builder.init_user_info(self.user_info)
        # default
        self.user_info.mother = 'World'
        if 'translation' not in self.user_info:
            self.user_info.translation = g4.G4ThreeVector()
        from scipy.spatial.transform import Rotation
        if 'rotation' not in self.user_info:
            self.user_info.rotation = Rotation.identity().as_matrix()
        if 'color' not in self.user_info:
            self.user_info.color = [1, 1, 1, 1]
        # common required keys
        self.required_keys = ['name', 'type', 'mother', 'material',
                              'translation', 'rotation', 'color']
        # additional required keys from the solid
        a = list(self.user_info.keys()) + self.required_keys
        self.required_keys = list(dict.fromkeys(a))

    def __del__(self):
        # for debug
        print('VolumeBase destructor')
        pass

    def __str__(self):
        # FIXME to modify according to the volume type,
        # for example with nb of copy (repeat), etc etc
        s = f'{self.user_info}'
        return s

    def check_user_info(self):
        # the list of required keys may be modified in the
        # classes that inherit from this one
        gam.assert_keys(self.required_keys, self.user_info)

        # check potential keys that are ignored
        for k in self.user_info.keys():
            if k not in self.required_keys:
                gam.warning(f'The key "{k}" is ignored in the volume : {self.user_info}')

    def construct(self, vol_manager):
        # check the user parameters
        self.check_user_info()

        # build the solid according to the type
        self.g4_solid = self.solid_builder.Build(self.user_info)

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
        transform = gam.get_vol_transform(vol)
        self.g4_physical_volume = g4.G4PVPlacement(transform,
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,  # volume name
                                                   mother_logical,  # mother volume or None if World
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking
