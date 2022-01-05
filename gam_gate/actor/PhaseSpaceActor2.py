import gam_gate as gam
import gam_g4 as g4


class PhaseSpaceActor2(g4.GamPhaseSpaceActor2, gam.ActorBase):
    """
    FIXME TODO
    """

    type_name = 'PhaseSpaceActor2'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # options
        user_info.attributes = []
        user_info.output = f'{user_info.name}.root'

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamPhaseSpaceActor2.__init__(self, user_info.__dict__)
        self.fStepFillNames = user_info.attributes  # this is a copy

    def __del__(self):
        pass

    def __str__(self):
        s = f'PhaseSpaceActor2 {self.user_info.name}'
        return s

    # not needed, only if need to do something from python
    def StartSimulationAction(self):
        g4.GamPhaseSpaceActor2.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamPhaseSpaceActor2.EndSimulationAction(self)
