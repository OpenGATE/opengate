import gam_gate as gam
import gam_g4 as g4


class HitsCollectionActor(g4.GamHitsCollectionActor, gam.ActorBase):
    """
    FIXME TODO
    """

    type_name = 'HitsCollectionActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        # fixme add options here
        user_info.branches = []
        user_info.output = None

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsCollectionActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.fStepFillNames = user_info.branches

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsCollectionActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        g4.GamHitsCollectionActor.StartSimulationAction(self)
        print('StartSimulationAction HitsCollectionActor')

    def EndSimulationAction(self):
        g4.GamHitsCollectionActor.EndSimulationAction(self)
        tree = self.GetHits()
        print('dump', self.user_info.output)
        tree.WriteToRoot(self.user_info.output)
        print('EndSimulationAction HitsCollectionActor')

    """def EndOfEventAction(self, event):
        g4.GamHitsCollectionActor.EndOfEventAction(self, event)
        print('EndOfEventAction HitsCollectionActor')
        print(event.GetEventID())"""
