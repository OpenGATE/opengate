import gam
import gam_g4 as g4


class VolumeBase:
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
        # note that the following keys are already checked
        # when building the volume tree
        self.required_keys = ['name', 'type', 'mother', 'material']

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

    def Construct(self, geom_manager):
        self.check_user_info()
        vol = self.user_info
        self.g4_solid = g4.G4Box(vol.name,  # name
                                 vol.size[0] / 2.0,
                                 vol.size[1] / 2.0,
                                 vol.size[2] / 2.0)  # half size in mm

        # FIXME replace by get_material
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

        if 'translation' not in vol:
            vol.translation = g4.G4ThreeVector()
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
