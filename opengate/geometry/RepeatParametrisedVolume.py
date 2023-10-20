import numpy as np
from scipy.spatial.transform import Rotation
from box import Box

import opengate_core as g4
from .VolumeBase import VolumeBase
from ..utility import fatal


class RepeatParametrisedVolume(VolumeBase):
    """
    Allow to repeat a volume with translations
    """

    type_name = "RepeatParametrised"

    @staticmethod
    def set_default_user_info(user_info):
        VolumeBase.set_default_user_info(user_info)
        user_info.material = "G4_AIR"
        user_info.repeated_volume_name = None
        user_info.linear_repeat = None
        user_info.translation = None
        user_info.rotation = Rotation.identity().as_matrix()
        user_info.offset = [0, 0, 0]
        user_info.start = None
        user_info.offset_nb = 1

    def __init__(self, user_info):
        super().__init__(user_info)

    def __del__(self):
        pass

    def construct_solid(self):
        # no solid to build
        pass

    def construct_logical_volume(self):
        # check
        if self.user_info.repeated_volume_name is None:
            fatal(
                f'Repeater "{self.user_info.name}": the option repeated_volume_name must be set'
            )
        if self.user_info.linear_repeat is None:
            fatal(
                f'Repeater "{self.user_info.name}": the option linear_repeat must be set'
            )
        # the repeated volume *must* have been build before
        v = self.volume_engine.get_volume(self.user_info.repeated_volume_name, False)
        # check phys vol
        if v.user_info.build_physical_volume:
            fatal(
                f"Error ! the volume {v.user_info.name} already have a physical volume. "
                f'Set "build_physical_volume" to False'
            )
        if v.g4_physical_volume:
            fatal(
                f"Error ! the volume {v.user_info.name} already have a physical volume. "
                f'Set "build_physical_volume" to False'
            )
        # set log vol
        self.g4_logical_volume = v.g4_logical_volume

    def construct_physical_volume(self):
        # find the mother's logical volume
        st = g4.G4LogicalVolumeStore.GetInstance()
        mother_logical = st.GetVolume(self.user_info.mother, False)
        if not mother_logical:
            fatal(f"The mother of {self.user_info.name} cannot be the world.")

        # create parameterised
        p = Box()
        p.linear_repeat = self.user_info.linear_repeat
        p.start = self.user_info.start
        p.translation = self.user_info.translation
        p.rotation = self.user_info.rotation
        if (  # FIXME put in helper functions
            p.rotation is None
            or not isinstance(p.rotation, (np.matrix, np.ndarray))
            or p.rotation.shape != (3, 3)
        ):
            p.rotation = Rotation.identity().as_matrix()
        p.offset = self.user_info.offset
        p.offset_nb = self.user_info.offset_nb
        self.param = g4.GateRepeatParameterisation()
        self.param.SetUserInfo(p)

        # number of copies
        n = p.linear_repeat[0] * p.linear_repeat[1] * p.linear_repeat[2] * p.offset_nb

        # (only daughter)
        # g4.EAxis.kUndefined => faster
        self.g4_physical_volume = g4.G4PVParameterised(
            self.user_info.name,
            self.g4_logical_volume,
            mother_logical,
            g4.EAxis.kUndefined,
            n,
            self.param,
            False,
        )  # very long if True

        self.g4_physical_volumes.append(self.g4_physical_volume)
