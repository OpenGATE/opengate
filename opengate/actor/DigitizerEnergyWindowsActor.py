import opengate as gate
import opengate_core as g4


class DigitizerEnergyWindowsActor(g4.GateDigitizerEnergyWindowsActor, gate.ActorBase):
    """
    Consider a list of hits and arrange them according to energy intervals.
    Input: one DigiCollection
    Output: as many DigiCollections as the number of energy windows
    """

    type_name = "DigitizerEnergyWindowsActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "EnergyWindows.root"
        user_info.input_digi_collection = "Hits"
        user_info.channels = []
        user_info.skip_attributes = []
        user_info.clear_every = 1e5

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateDigitizerEnergyWindowsActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerEnergyWindowsActor {self.user_info.name}"
        return s

    def StartSimulationAction(
        self,
    ):  # not needed, only if need to do something in python
        g4.GateDigitizerEnergyWindowsActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerEnergyWindowsActor.EndSimulationAction(self)
