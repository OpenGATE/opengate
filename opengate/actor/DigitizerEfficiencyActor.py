import opengate as gate
import opengate_core as g4


class DigitizerEfficiencyActor(g4.GateDigitizerEfficiencyActor, gate.ActorBase):
    """
    Digitizer module for simulating efficiency.
    """

    type_name = "DigitizerEfficiencyActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "efficiency.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.efficiency = 1.0  # keep everything

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        gate.ActorBase.__init__(self, user_info)
        g4.GateDigitizerEfficiencyActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        efficiency = user_info.efficiency
        if not (0.0 <= efficiency <= 1.0):
            gate.warning(f"Efficency set to {efficiency}, which is not in [0;1].")

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerEfficiencyActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerEfficiencyActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerEfficiencyActor.EndSimulationAction(self)
