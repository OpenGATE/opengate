import gam
import gam_g4 as g4


class VolumeBase:  # FIXME rename to Volume ?
    """
        FIXME
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
        # common required keys
        self.required_keys = ['name', 'type', 'mother', 'material', 'translation']
        # additional required keys from the solid
        a = list(self.user_info.keys()) + self.required_keys
        self.required_keys = list(dict.fromkeys(a))

    def __del__(self):
        print('VolumeBase destructor')

    def __str__(self):
        # FIXME to modify according to the volume type,
        # for example with nb of copy (repeat), etc etc
        s = f'{self.user_info}'
        return s

    def check_user_info(self):
        # the list of required keys may be modified in the
        # classes that inherit from this one
        gam.assert_keys(self.required_keys, self.user_info)

        # FIXME Check here for potential new key that are ignored
        for k in self.user_info.keys():
            if k not in self.required_keys:
                gam.warning(f'The key "{k}" is ignored in the volume : {self.user_info}')

    def Construct(self, geom_manager):
        # check the user parameters
        self.check_user_info()

        # build the solid according to the type
        self.g4_solid = self.solid_builder.Build(self.user_info)

        # FIXME replace by get_material
        vol = self.user_info
        material = geom_manager.g4_materials[vol.material]
        self.g4_logical_volume = g4.G4LogicalVolume(self.g4_solid,  # solid
                                                    material,  # material
                                                    vol.name)  # name
        # FIXME replace by get_logical_volume
        if vol.mother:
            st = g4.G4LogicalVolumeStore.GetInstance()
            mother_logical = st.GetVolume(vol.mother, False)
            print(mother_logical)
            # mother_logical = geom_manager.g4_logical_volumes[vol.mother]
        else:
            mother_logical = None

        self.g4_physical_volume = g4.G4PVPlacement(None,  # no rotation
                                                   g4.G4ThreeVector(vol.translation[0],
                                                                    vol.translation[1],
                                                                    vol.translation[2]),  #
                                                   self.g4_logical_volume,  # logical volume
                                                   vol.name,
                                                   mother_logical,  # no mother volume
                                                   False,  # no boolean operation
                                                   0,  # copy number
                                                   True)  # overlaps checking
