from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units
from .actoroutput import ActorOutputStatisticsActor
from ..base import process_cls


class SimulationStatisticsActor(ActorBase, g4.GateSimulationStatisticsActor):
    """
    Store statistics about a simulation run.
    """

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

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output(ActorOutputStatisticsActor, "stats")
        self.user_output.stats.set_write_to_disk(False)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateSimulationStatisticsActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def __str__(self):
        s = self.user_output["stats"].__str__()
        return s

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInput(self.user_info)
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


class KillActor(ActorBase, g4.GateKillActor):

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
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def EndSimulationAction(self):
        self.number_of_killed_particles = self.GetNumberOfKilledParticles()


def _setter_hook_particles(self, value):
    if isinstance(value, str):
        return [value]
    else:
        return list(value)


class SplittingActorBase(ActorBase):
    # hints for IDE
    splitting_factor: int
    bias_primary_only: bool
    bias_only_once: bool
    particles: list

    user_info_defaults = {
        "splitting_factor": (
            1,
            {
                "doc": "FIXME",
            },
        ),
        "bias_primary_only": (
            True,
            {
                "doc": "FIXME",
            },
        ),
        "bias_only_once": (
            True,
            {
                "doc": "FIXME",
            },
        ),
        "particles": (
            [
                "all",
            ],
            {
                "doc": "FIXME",
                "setter_hook": _setter_hook_particles,
            },
        ),
    }


class ComptSplittingActor(SplittingActorBase, g4.GateOptrComptSplittingActor):
    # hints for IDE
    weight_threshold: float
    min_weight_of_particle: float
    russian_roulette: bool
    rotation_vector_director: bool
    vector_director: list
    max_theta: float

    user_info_defaults = {
        "weight_threshold": (
            0,
            {
                "doc": "FIXME",
            },
        ),
        "min_weight_of_particle": (
            0,
            {
                "doc": "FIXME",
            },
        ),
        "russian_roulette": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "rotation_vector_director": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "vector_director": (
            [0, 0, 1],
            {
                "doc": "FIXME",
            },
        ),
        "max_theta": (
            90 * g4_units.deg,
            {
                "doc": "FIXME",
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
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()


class BremSplittingActor(SplittingActorBase, g4.GateBOptrBremSplittingActor):
    # hints for IDE
    processes: list

    user_info_defaults = {
        "processes": (
            ["eBrem"],
            {
                "doc": "FIXME",
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
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()


process_cls(ActorOutputStatisticsActor)
process_cls(SimulationStatisticsActor)
process_cls(KillActor)
process_cls(SplittingActorBase)
process_cls(ComptSplittingActor)
process_cls(BremSplittingActor)
