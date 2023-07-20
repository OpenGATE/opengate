from .DigitizerHitsCollectionActor import *


class ARFTrainingDatasetActor(g4.GateARFTrainingDatasetActor, gate.ActorBase):
    """
    The ARFTrainingDatasetActor build a root file with energy, angles, positions and energy windows
    of a spect detector. To be used by garf_train to train a ARF neural network.

    Note: Must inherit from ActorBase not from HitsCollectionActor, even if the
    cpp part inherit from HitsCollectionActor
    """

    type_name = "ARFTrainingDatasetActor"

    @staticmethod
    def set_default_user_info(user_info):
        DigitizerHitsCollectionActor.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "arf_training.root"
        user_info.debug = False
        user_info.energy_windows_actor = None
        user_info.russian_roulette = 1

    def __init__(self, user_info):
        gate.ActorBase.__init__(self, user_info)
        g4.GateARFTrainingDatasetActor.__init__(self, user_info.__dict__)

    def __del__(self):
        pass

    def initialize(self, simulation_engine_wr=None):
        gate.ActorBase.initialize(self, simulation_engine_wr)
        # check the energy_windows_actor
        ewa_name = self.user_info.energy_windows_actor
        ewa = self.simulation.get_actor_user_info(ewa_name)
        if ewa.type_name != "DigitizerEnergyWindowsActor":
            gate.fatal(
                f"In the actor '{self.user_info.name}', the parameter 'energy_windows_actor' is {ewa.type_name}"
                f" while it must be a DigitizerEnergyWindowsActor"
            )

    def __str__(self):
        s = f"ARFTrainingDatasetActor {self.user_info.name}"
        return s
