from box import Box
import opengate_core as g4

from .base import ActorBase
from .actoroutput import ActorOutputBase
from ..serialization import dump_json
from ..exception import warning
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


def _setter_hook_chem_actor_output_filename(self, output_filename):
    if output_filename != "" and output_filename is not None:
        self.write_to_disk = True
    return output_filename


class ActorOutputChemicalStageActor(ActorOutputBase):
    user_info_defaults = {
        "encoder": (
            "json",
            {
                "doc": "How should the chemistry output be encoded?",
                "allowed_values": ("json",),
            },
        ),
        "output_filename": (
            "auto",
            {
                "doc": "Filename for the chemistry-stage output.",
                "setter_hook": _setter_hook_chem_actor_output_filename,
            },
        ),
        "write_to_disk": (
            False,
            {
                "doc": "Should the chemistry-stage output be written to disk?",
            },
        ),
        "active": (
            True,
            {"doc": "This output is always active.", "read_only": True},
        ),
    }

    default_suffix = "json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.merged_data = Box(
            {
                "killed_particles": 0,
                "aborted_events": 0,
                "chemistry_starts": 0,
                "chemistry_stages": 0,
                "pre_time_step_calls": 0,
                "post_time_step_calls": 0,
                "reaction_count": 0,
                "recorded_events": 0,
                "accumulated_primary_energy_loss": 0.0,
                "total_energy_deposit": 0.0,
                "mean_restricted_let": 0.0,
                "std_restricted_let": 0.0,
                "species": {},
                "reactions": {},
                "times_to_record": [],
            }
        )

    def store_data(self, data, **kwargs):
        self.merged_data = Box(data)

    def get_data(self, **kwargs):
        if "which" in kwargs and kwargs["which"] != "merged":
            warning(
                "The chemistry-stage actor output only stores merged data currently. "
                f"The which={kwargs['which']} you provided will be ignored."
            )
        return self.merged_data

    def get_processed_output(self):
        return self.merged_data

    def __str__(self):
        d = self.merged_data
        lines = [
            f"recorded_events         {d.recorded_events}",
            f"killed_particles       {d.killed_particles}",
            f"aborted_events         {d.aborted_events}",
            f"chemistry_starts       {d.chemistry_starts}",
            f"chemistry_stages       {d.chemistry_stages}",
            f"reaction_count         {d.reaction_count}",
            f"mean_restricted_let    {d.mean_restricted_let}",
            f"std_restricted_let     {d.std_restricted_let}",
            f"total_energy_deposit   {d.total_energy_deposit}",
            f"primary_energy_loss    {d.accumulated_primary_energy_loss}",
            f"species_times          {len(d.times_to_record)}",
        ]
        return "\n".join(lines)

    def write_data(self, **kwargs):
        with open(self.get_output_path(which="merged"), "w+") as f:
            dump_json(self.get_processed_output(), f, indent=4)

    def write_data_if_requested(self, **kwargs):
        if self.write_to_disk is True:
            self.write_data(**kwargs)


class ChemicalStageActor(ChemistryActorBase, g4.GateChemicalStageActor):
    """
    Minimal chemistry-aware actor inspired by chem6.

    It currently provides:
    - chem6-like primary killer logic
    - restricted LET scoring
    - chemistry-time species sampling
    - reaction counting
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
        "min_kinetic_energy": (
            0.0,
            {"doc": "Kill the tracked primary when its kinetic energy falls below this value."},
        ),
        "bounding_box_size": (
            [0.0, 0.0, 0.0],
            {"doc": "Size of the optional bounding box used to kill tracks outside the region."},
        ),
        "use_bounding_box": (
            False,
            {"doc": "Enable the bounding-box track killing logic."},
        ),
        "let_cutoff": (
            1e30,
            {"doc": "Restricted LET cutoff energy. Secondary kinetic energies below this threshold are added to the event energy deposit."},
        ),
        "times_to_record": (
            [],
            {"doc": "Explicit chemistry times at which species numbers and G values should be recorded."},
        ),
        "number_of_time_bins": (
            10,
            {"doc": "If > 0 and times_to_record is empty, generate logarithmically spaced chemistry scoring times like chem6."},
        ),
    }

    user_output_config = {
        "results": {
            "actor_output_class": ActorOutputChemicalStageActor,
        },
    }

    def __init__(self, *args, **kwargs):
        ChemistryActorBase.__init__(self, *args, **kwargs)
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
                "UserReactionAction",
                "EndOfEventAction",
                "EndProcessing",
                "EndSimulationAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def EndSimulationAction(self):
        data = {
            "killed_particles": self.GetNumberOfKilledParticles(),
            "aborted_events": self.GetNumberOfAbortedEvents(),
            "chemistry_starts": self.GetNumberOfChemistryStarts(),
            "chemistry_stages": self.GetNumberOfChemistryStages(),
            "pre_time_step_calls": self.GetNumberOfPreTimeStepCalls(),
            "post_time_step_calls": self.GetNumberOfPostTimeStepCalls(),
            "reaction_count": self.GetNumberOfReactions(),
            "recorded_events": self.GetNumberOfRecordedEvents(),
            "accumulated_primary_energy_loss": self.GetAccumulatedPrimaryEnergyLoss(),
            "total_energy_deposit": self.GetAccumulatedEnergyDeposit(),
            "mean_restricted_let": self.GetMeanRestrictedLET(),
            "std_restricted_let": self.GetStdRestrictedLET(),
            "species": self.GetSpeciesInfo(),
            "reactions": self.GetReactionCounts(),
            "times_to_record": self.GetRecordedTimes(),
        }
        self.user_output.results.store_data(data)


process_cls(ChemistryActorBase)
process_cls(ActorOutputChemicalStageActor)
process_cls(ChemicalStageActor)
