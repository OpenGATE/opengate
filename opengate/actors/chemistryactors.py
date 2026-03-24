import opengate_core as g4

from .base import ActorBase
from ..base import process_cls


class ChemistryActorBase(ActorBase):
    """
    Base class for chemistry-aware actors.

    The class itself is intentionally light: chemistry participation is mainly
    implemented through the C++ GateVChemistryActor side, while Python uses the
    type for configuration, validation and actor discovery.
    """

    user_info_defaults = {}

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)


class ChemicalStageActor(ChemistryActorBase, g4.GateChemicalStageActor):
    """
    Minimal chemistry-aware actor inspired by chem6.

    It currently provides:
    - primary energy-loss tracking
    - optional primary kill / event abort thresholds
    - optional bounding-box killing
    - counters for chemistry scheduler activity
    """

    user_info_defaults = {
        "track_only_primary": (
            True,
            {"doc": "Apply the chem6-like energy-loss logic only to the primary track."},
        ),
        "primary_pdg_code": (
            11,
            {"doc": "PDG code of the primary particle for the chem6-like logic."},
        ),
        "energy_loss_min": (
            -1.0,
            {"doc": "Kill the tracked primary when accumulated energy loss exceeds this value. Negative disables it."},
        ),
        "energy_loss_max": (
            -1.0,
            {"doc": "Abort the event when accumulated energy loss exceeds this value. Negative disables it."},
        ),
        "bounding_box_size": (
            [0.0, 0.0, 0.0],
            {"doc": "Size of the optional bounding box used to kill tracks outside the region."},
        ),
        "use_bounding_box": (
            False,
            {"doc": "Enable the bounding-box track killing logic."},
        ),
    }

    def __init__(self, *args, **kwargs):
        ChemistryActorBase.__init__(self, *args, **kwargs)
        self.number_of_killed_particles = 0
        self.number_of_aborted_events = 0
        self.number_of_chemistry_starts = 0
        self.number_of_pre_time_step_calls = 0
        self.number_of_post_time_step_calls = 0
        self.accumulated_primary_energy_loss = 0.0
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateChemicalStageActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "StartSimulationAction",
                "BeginOfEventAction",
                "SteppingAction",
                "NewStage",
                "StartProcessing",
                "UserPreTimeStepAction",
                "UserPostTimeStepAction",
                "EndProcessing",
                "EndSimulationAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def EndSimulationAction(self):
        self.number_of_killed_particles = self.GetNumberOfKilledParticles()
        self.number_of_aborted_events = self.GetNumberOfAbortedEvents()
        self.number_of_chemistry_starts = self.GetNumberOfChemistryStarts()
        self.number_of_pre_time_step_calls = self.GetNumberOfPreTimeStepCalls()
        self.number_of_post_time_step_calls = self.GetNumberOfPostTimeStepCalls()
        self.accumulated_primary_energy_loss = (
            self.GetAccumulatedPrimaryEnergyLoss()
        )


process_cls(ChemistryActorBase)
process_cls(ChemicalStageActor)
