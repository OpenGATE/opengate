import gam_gate as gam
import gam_g4 as g4


class HitsEnergyWindowsActor(g4.GamHitsEnergyWindowsActor, gam.ActorBase):
    """
    FIXME TODO
    """

    type_name = 'HitsEnergyWindowsActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # fixme add options here
        user_info.attributes = []
        user_info.output = 'EnergyWindows.root'
        user_info.input_hits_collection = 'Hits'
        user_info.channels = []
        user_info.skip_attributes = []

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsEnergyWindowsActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsEnergyWindowsActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        g4.GamHitsEnergyWindowsActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamHitsEnergyWindowsActor.EndSimulationAction(self)
