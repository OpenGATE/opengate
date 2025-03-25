import opengate_core as g4
from ..utility import g4_units
from .base import ActorBase
from ..base import process_cls


class ChemistryActor(ActorBase, g4.GateChemistryActor):
    """ """

    # hints for IDE

    user_info_defaults = {
        "output": (
            "output.root",
            {
                "doc": "output file",
            },
        ),
        "timestep_model": (
            "IRT",
            {
                "doc": "timestep model: {IRT, IRT_syn, SBS}",
            },
        ),
        "reactions": (
            [],
            {
                "doc": "list of reactions TODO",
            },
        ),
        "default_reactions": (
            True,
            {
                "doc": "autofill reactions with defaults from G4",
            },
        ),
        "end_time": (
            1 * g4_units.s,
            {
                "doc": "end time",
            },
        ),
        "time_bins_count": (
            10,
            {
                "doc": "time bins count",
            },
        ),
        "molecule_counter_verbose": (
            0,
            {
                "doc": "verbose level of molecule counter",
            },
        ),
    }

    user_output_config = {}

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateChemistryActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "EndOfRunAction",
                "EndOfEventAction",
                "SteppingAction",
                "EndSimulationAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateChemistryActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateChemistryActor.EndSimulationAction(self)


process_cls(ChemistryActor)
