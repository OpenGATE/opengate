import opengate as gate
import opengate_core as g4


class PhaseSpaceActor(g4.GatePhaseSpaceActor, gate.ActorBase):
    """
    Similar to HitsCollectionActor : store a list of hits.
    However only the first hit of given event is stored here.
    """

    type_name = "PhaseSpaceActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        # options
        user_info.attributes = []
        user_info.output = f"{user_info.name}.root"
        user_info.store_absorbed_event = False
        user_info.debug = False

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GatePhaseSpaceActor.__init__(self, user_info.__dict__)
        self.fStepFillNames = user_info.attributes  # this is a copy

    def __del__(self):
        pass

    def __str__(self):
        s = f"PhaseSpaceActor {self.user_info.name}"
        return s

    # not needed, only if need to do something from python
    def StartSimulationAction(self):
        g4.GatePhaseSpaceActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GatePhaseSpaceActor.EndSimulationAction(self)
