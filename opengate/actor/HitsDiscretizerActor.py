import opengate as gate
import opengate_core as g4


class HitsDiscretizerActor(g4.GateHitsDiscretizerActor, gate.ActorBase):
    """
    FIXME
    """

    type_name = "HitsDiscretizerActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_hits_collection = "Hits"
        user_info.discrete_position_volume = [False, False, False]
        user_info.clear_every = 1e5

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateHitsDiscretizerActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        self.fStepFillNames = user_info.attributes

    def __del__(self):
        pass

    def __str__(self):
        s = f"HitsDiscretizerActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        # create list of discrete position ?
        sim = self.simulation
        vname = "pet_crystal"
        depth = sim.volume_manager.get_volume_depth(vname)
        print(depth)
        self.SetVolumeDepth(depth, depth, depth)
        g4.GateHitsDiscretizerActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateHitsDiscretizerActor.EndSimulationAction(self)
