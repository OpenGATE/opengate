import gam_gate as gam
import gam_g4 as g4


class HitsCollectionActor(g4.GamHitsCollectionActor, gam.ActorBase):
    """
    Build a list of hits in a given volume.
    - the list of attributes to be stored is given in the 'attributes' options
    - output as root
    """

    type_name = 'HitsCollectionActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = 'hits.root'

    def __init__(self, user_info):
        gam.ActorBase.__init__(self, user_info)
        g4.GamHitsCollectionActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction'}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes

    def __del__(self):
        pass

    def __str__(self):
        s = f'HitsCollectionActor {self.user_info.name}'
        return s

    def StartSimulationAction(self):  # not needed, only if need to do something in python
        g4.GamHitsCollectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GamHitsCollectionActor.EndSimulationAction(self)
