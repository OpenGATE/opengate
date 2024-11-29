from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units
from .actoroutput import ActorOutputStatisticsActor
from ..utility import g4_units, g4_best_unit_tuple
from .actoroutput import ActorOutputBase
from ..serialization import dump_json
from ..exception import fatal, warning
from ..base import process_cls
from anytree import Node, RenderTree


class SimulationStatisticsActor(ActorBase, g4.GateSimulationStatisticsActor):
    """Store statistics about a simulation run."""

    # hints for IDE
    track_types_flag: bool

    user_info_defaults = {
        "track_types_flag": (
            False,
            {
                "doc": "Should the type of tracks be counted?",
            },
        ),
    }

    user_output_config = {
        "stats": {
            "actor_output_class": ActorOutputStatisticsActor,
        },
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        # self._add_user_output(ActorOutputStatisticsActor, "stats")
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateSimulationStatisticsActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    @property
    def counts(self):
        return self.user_output.stats.merged_data

    def __str__(self):
        s = self.user_output["stats"].__str__()
        return s

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateSimulationStatisticsActor.StartSimulationAction(self)
        # self.user_output.stats.merged_data.nb_threads = (
        #     self.simulation.number_of_threads
        # )

    # def EndOfRunActionMasterThread(self, run_index):
    # self.user_output.stats.store_data()

    def EndSimulationAction(self):
        g4.GateSimulationStatisticsActor.EndSimulationAction(self)

        data = dict([(k, v) for k, v in self.GetCounts().items()])

        if self.simulation is not None:
            sim_start = self.simulation.run_timing_intervals[0][0]
        else:
            sim_start = 0

        if self.simulation is not None:
            sim_stop = self.simulation.run_timing_intervals[-1][1]
        else:
            sim_stop = 0

        data["sim_start"] = sim_start
        data["sim_stop"] = sim_stop
        data["sim_start_time"] = self.simulation.run_timing_intervals[0][0]
        data["sim_stop_time"] = self.simulation.run_timing_intervals[-1][1]
        data["nb_threads"] = self.simulation.number_of_threads
        self.user_output.stats.store_data("merged", data)

        self.user_output.stats.write_data_if_requested()

    def EndOfMultiProcessAction(self):
        self.user_output.stats.write_data_if_requested()


"""
    It is feasible to get callback every Run, Event, Track, Step in the python side.
    However, it is VERY time consuming. For SteppingAction, expect large performance drop.
    It could be however useful for prototyping or tests.

    it requires "trampoline functions" on the cpp side.

    # it is feasible but very slow !
    def SteppingAction(self, step, touchable):
        g4.GateSimulationStatisticsActor.SteppingAction(self, step, touchable)
        do_something()
"""


class ActorOutputKillAccordingProcessesActor(ActorOutputBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number_of_killed_particles = 0

    def get_processed_output(self):
        d = {}
        d["particles killed"] = self.number_of_killed_particles
        return d

    def __str__(self):
        s = ""
        for k, v in self.get_processed_output().items():
            s = k + ": " + str(v)
            s += "\n"
        return s


class KillAccordingProcessesActor(ActorBase, g4.GateKillAccordingProcessesActor):
    # hints for IDE
    processes_to_kill: list
    is_rayleigh_an_interaction: bool

    """
    This actor enables the user to kill particles according to one or more processes which occur in a volume. If the user
    wants to kill a particle whenever a proces occurs (except transportation), the "all" option is available.
    """

    user_info_defaults = {
        "processes_to_kill": (
            [],
            {
                "doc": "If a processes belonging to this list occured, the particle and its potential secondaries are killed. the variable all can be set up to kill a particle if an interaction occured."
            },
        ),
        "is_rayleigh_an_interaction": (
            True,
            {
                "doc": "Specific case to be faster. If a user wants to kill all interactions which implies an energy loss, this boolean enables to not account Rayleigh process as an interaction"
            },
        ),
    }

    """
    If a particle, not generated or generated within the volume at which our actor is attached, crosses the volume
    without interaction, the particle is killed.
    """

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output(
            ActorOutputKillAccordingProcessesActor, "kill_interacting_particles"
        )
        self.__initcpp__()
        self.number_of_killed_particles = 0

    def __initcpp__(self):
        g4.GateKillAccordingProcessesActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "BeginOfRunAction",
                "BeginOfEventAction",
                "PreUserTrackingAction",
                "SteppingAction",
                "EndSimulationAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        if len(self.user_info.processes_to_kill) == 0:
            fatal("You have to select at least one process ! ")

    def EndSimulationAction(self):
        self.user_output.kill_interacting_particles.number_of_killed_particles = (
            self.number_of_killed_particles
        )

    def __str__(self):
        s = self.user_output["kill_non_interacting_particles"].__str__()
        return s


class KillActor(ActorBase, g4.GateKillActor):
    """Actor which kills a particle entering a volume."""

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.number_of_killed_particles = 0
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateKillActor.__init__(self, self.user_info)
        self.AddActions(
            {"StartSimulationAction", "EndSimulationAction", "SteppingAction"}
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def EndSimulationAction(self):
        self.number_of_killed_particles = self.GetNumberOfKilledParticles()


def _setter_hook_particles(self, value):
    if isinstance(value, str):
        return [value]
    else:
        return list(value)


class SplittingActorBase(ActorBase):
    """Actors based on the G4GenericBiasing class of GEANT4. This class provides tools to interact with GEANT4 processes
    during a simulation, allowing direct modification of process properties. Additionally, it enables non-physics-based
    particle splitting (e.g., pure geometrical splitting) to introduce biasing into simulations. SplittingActorBase
    serves as a foundational class for particle splitting operations, with parameters for configuring the splitting
    behavior based on various conditions.
    """

    # hints for IDE
    splitting_factor: int
    bias_primary_only: bool
    bias_only_once: bool
    particles: list

    user_info_defaults = {
        "splitting_factor": (
            1,
            {
                "doc": "Specifies the number of particles to generate each time the splitting mechanism is applied",
            },
        ),
        "bias_primary_only": (
            True,
            {
                "doc": "If true, the splitting mechanism is applied only to particles with a ParentID of 1",
            },
        ),
        "bias_only_once": (
            True,
            {
                "doc": "If true, the splitting mechanism is applied only once per particle history",
            },
        ),
        "particles": (
            [
                "all",
            ],
            {
                "doc": "Specifies the particles to split. The default value, all, includes all particles",
                "setter_hook": _setter_hook_particles,
            },
        ),
    }


class ComptSplittingActor(SplittingActorBase, g4.GateOptrComptSplittingActor):
    """This splitting actor enables process-based splitting specifically for Compton interactions. Each time a Compton
    process occurs, its behavior is modified by generating multiple Compton scattering tracks
    (splitting factor - 1 additional tracks plus the original) associated with the initial particle.
    Compton electrons produced in the interaction are also included, in accordance with the secondary cut settings
    provided by the user.
    """

    # hints for IDE
    min_weight_of_particle: float
    russian_roulette: bool
    rotation_vector_director: bool
    vector_director: list
    max_theta: float

    user_info_defaults = {
        "min_weight_of_particle": (
            0,
            {
                "doc": "Defines a minimum weight for particles. Particles with weights below this threshold will not be split, limiting the splitting cascade of low-weight particles generated during Compton interactions.",
            },
        ),
        "russian_roulette": (
            False,
            {
                "doc": "If enabled (True), applies a Russian roulette mechanism. Particles emitted in undesired directions are discarded if a random number exceeds 1 / splitting_factor",
            },
        ),
        "vector_director": (
            [0, 0, 1],
            {
                "doc": "Specifies the particle’s direction of interest for the Russian roulette. In this direction, the Russian roulette is not applied",
            },
        ),
        "rotation_vector_director": (
            False,
            {
                "doc": "If enabled, allows the vector_director to rotate based on any rotation applied to a volume to which this actor is attached",
            },
        ),
        "max_theta": (
            90 * g4_units.deg,
            {
                "doc": "Sets the angular range (in degrees) around vector_director within which the Russian roulette mechanism is not applied.",
            },
        ),
    }

    processes = ("compt",)

    def __init__(self, *args, **kwargs):
        SplittingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateOptrComptSplittingActor.__init__(self, {"name": self.name})

    def initialize(self):
        SplittingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


class BremSplittingActor(SplittingActorBase, g4.GateBOptrBremSplittingActor):
    """This splitting actor enables process-based splitting specifically for bremsstrahlung process. Each time a Brem
    process occurs, its behavior is modified by generating multiple secondary Brem scattering tracks
    (splitting factor) attached to  the initial charged particle.
    """

    # hints for IDE
    processes: list

    user_info_defaults = {
        "processes": (
            ["eBrem"],
            {
                "doc": "Specifies the process split by this actor. This parameter is set to eBrem, as the actor is specifically developed for this process. It is recommended not to modify this setting.",
            },
        ),
    }

    processes = ("eBrem",)

    def __init__(self, *args, **kwargs):
        SplittingActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateBOptrBremSplittingActor.__init__(self, {"name": self.name})

    def initialize(self):
        SplittingActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()


process_cls(ActorOutputStatisticsActor)
process_cls(SimulationStatisticsActor)
process_cls(KillActor)
process_cls(ActorOutputKillAccordingProcessesActor)
process_cls(KillAccordingProcessesActor)
process_cls(SplittingActorBase)
process_cls(ComptSplittingActor)
process_cls(BremSplittingActor)
