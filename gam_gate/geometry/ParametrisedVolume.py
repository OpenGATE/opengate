import gam_gate as gam
import gam_g4 as g4
import itk
import numpy as np
from box import Box


class ParametrisedVolume(gam.VolumeBase):
    """
        Store information about a voxelized volume
    """

    type_name = 'Parametrised'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        user_info.material = 'G4_AIR'
        user_info.repeated_vol = None

    def __init__(self, user_info):
        super().__init__(user_info)

    def __del__(self):
        pass

    def construct_solid(self):
        print('nothing to do for construct_solid')

    def construct_logical_volume(self):
        print('construct_logical_volume')
        ## FiXME check if already build !?
        v = self.volume_manager.get_volume(self.user_info.repeated_vol, False)
        print(v)
        self.g4_logical_volume = v.g4_logical_volume
        print(self.g4_logical_volume)

    def construct_physical_volume(self):
        print('construct PV parametrised')
        print(self.user_info.repeated_vol)

        # FIXME color attributes like VolumeBase

        print('name', self.user_info.name)
        print('repeated vol name', self.user_info.repeated_vol)
        print('mother', self.user_info.mother)

        # find the mother's logical volume
        mother_logical = None
        st = g4.G4LogicalVolumeStore.GetInstance()
        mother_logical = st.GetVolume(self.user_info.mother, False)
        if not mother_logical:
            gam.fatal(f'The mother of {self.user_info.name} cannot be the world.')
        print('mother log', mother_logical)

        # FIXME -> parameter
        mm = gam.g4_units('mm')
        hole_translation = [2.94449 * mm, 1.7 * mm, 0]
        hole_repeat = [183, 235, 1]
        #hole_repeat = [48, 30, 1]
        hole2_offset = [1.47224 * mm, 0.85 * mm, 0]
        start = [-(hole_repeat[0] * hole_translation[0]) / 2.0,
                 -(hole_repeat[1] * hole_translation[1]) / 2.0, 0]


        self.param = g4.GamRepeatParameterisation()
        p = Box()
        p.start = start
        p.translation = hole_translation
        p.offset = hole2_offset
        p.offset_nb = 2
        p.repeat = hole_repeat
        self.param.SetUserInfo(p)

        n = hole_repeat[0] * hole_repeat[1] * hole_repeat[2] * p.offset_nb
        print(f'{n=}')

        # (only daughter)
        # g4.EAxis.kUndefined => faster
        self.g4_physical_volume = g4.G4PVParameterised(self.user_info.name,
                                                       self.g4_logical_volume,
                                                       mother_logical,
                                                       g4.EAxis.kUndefined,
                                                       n,
                                                       self.param,
                                                       False)  ## very long if True

        self.g4_physical_volumes.append(self.g4_physical_volume)
