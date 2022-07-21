import gam_g4 as g4
import itk
import numpy as np
import gam_gate as gam
from scipy.spatial.transform import Rotation


class ARFActor(g4.GamARFActor, gam.ActorBase):
    """
    TODO
    """

    type_name = 'ARFActor'

    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # required user info, default values
        user_info.arf_detector = None
        user_info.batch_size = 100  ## FIXME

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamARFActor.__init__(self, user_info.__dict__)

    def __str__(self):
        u = self.user_info
        s = f'ARFActor "{u.name}"'
        return s

    def initialize(self):
        print('arf actor initialize')
        gam.ActorBase.initialize(self)
        self.user_info.arf_detector.initialize(self)
        self.ActorInitialize()
        self.SetARFFunction(self.user_info.arf_detector.apply)

    def StartSimulationAction(self):
        print('ARF Actor StartSimulationAction')

    def EndSimulationAction(self):
        g4.GamARFActor.EndSimulationAction(self)
        print('ARF Actor EndSimulationAction')
        self.user_info.arf_detector.apply(self)
