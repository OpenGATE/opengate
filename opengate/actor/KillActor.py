import opengate_core as g4
import itk
import numpy as np
import opengate as gate
from scipy.spatial.transform import Rotation


class KillActor(g4.GateKillActor, gate.ActorBase):
    type_name = "KillActor"

    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.kill = True

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateKillActor.__init__(self, user_info.__dict__)
