import opengate as gate
import opengate_core as g4


class DigitizerAdderActor(g4.GateDigitizerAdderActor, gate.ActorBase):
    """
    Equivalent to Gate "adder": gather all hits of an event in the same volume.
    Input: a HitsCollection, need aat least TotalEnergyDeposit and PostPosition attributes
    Output: a Single collections

    Policies:
    - EnergyWinnerPosition: consider position and energy of the hit with the max energy
       for all other attributes (Time, etc.): the value of the winner is used.
    - EnergyWeightedCentroidPosition: computed the energy-weighted centroid position
       for all other attributes (Time, etc.): the value the last seen hit is used.

    """

    type_name = "DigitizerAdderActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.policy = "EnergyWinnerPosition"  # EnergyWeightedCentroidPosition
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.group_volume = None

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateDigitizerAdderActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)
        if (
            user_info.policy != "EnergyWinnerPosition"
            and user_info.policy != "EnergyWeightedCentroidPosition"
        ):
            gate.fatal(
                f"Error, the policy for the Adder '{user_info.name}' must be EnergyWinnerPosition or "
                f"EnergyWeightedCentroidPosition, while is is '{user_info.policy}'"
            )

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerAdderActor {self.user_info.name}"
        return s

    def set_group_by_depth(self):
        depth = -1
        if self.user_info.group_volume is not None:
            depth = self.simulation.volume_manager.get_volume_depth(
                self.user_info.group_volume
            )
        self.SetGroupVolumeDepth(depth)

    def StartSimulationAction(self):
        self.set_group_by_depth()
        g4.GateDigitizerAdderActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerAdderActor.EndSimulationAction(self)
