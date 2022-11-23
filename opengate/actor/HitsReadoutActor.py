import opengate as gate
import opengate_core as g4


class HitsReadoutActor(g4.GateHitsReadoutActor, gate.ActorBase):
    """
    This actor is a HitsAdderActor + a discretization step:
    the final position is the center of the volume
    """

    type_name = "HitsReadoutActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.HitsAdderActor.set_default_user_info(user_info)
        user_info.discretize_volume = None

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateHitsReadoutActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"HitsReadoutActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        gate.HitsAdderActor.set_group_by_depth(self)
        if self.user_info.discretize_volume is None:
            gate.fatal(f'Please, set the option "discretize_volume"')
        sim = self.simulation
        depth = sim.volume_manager.get_volume_depth(self.user_info.discretize_volume)
        self.SetDiscretizeVolumeDepth(depth)
        g4.GateHitsReadoutActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateHitsReadoutActor.EndSimulationAction(self)
