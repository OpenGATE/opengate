import gam
import gam_g4 as g4


class PhaseSpaceActor(g4.GamPhaseSpaceActor, gam.ActorBase):
    """
    FIXME TODO
    """

    type_name = 'PhaseSpaceActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # fixme add options here
        user_info.branches = []
        user_info.output = f'{user_info.name}.root'

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamPhaseSpaceActor.__init__(self, user_info.__dict__)
        # actions are also set from the cpp side
        self.fActions.append('StartSimulationAction')
        self.fActions.append('EndSimulationAction')
        self.fActions.append('BeginOfRunAction')
        self.fActions.append('SteppingAction')  ## FIXME does not work ???
        self.fStepFillNames = user_info.branches

    def __del__(self):
        pass

    def __str__(self):
        s = f'PhaseSpaceActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        g4.GamPhaseSpaceActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamPhaseSpaceActor.EndSimulationAction(self)
