import opengate as gate
import opengate_core as g4


class HitsCollectionActor(g4.GateHitsCollectionActor, gate.ActorBase):
    """
    Build a list of hits in a given volume.
    - the list of attributes to be stored is given in the 'attributes' options
    - output as root
    """

    type_name = "HitsCollectionActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "hits.root"
        user_info.debug = False
        user_info.clear_every = 1e5

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateHitsCollectionActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes

    def __del__(self):
        pass

    def __str__(self):
        s = f"HitsCollectionActor {self.user_info.name}"
        return s

    def StartSimulationAction(
        self,
    ):  # not needed, only if need to do something in python
        g4.GateHitsCollectionActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateHitsCollectionActor.EndSimulationAction(self)
