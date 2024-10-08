from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units, g4_best_unit_tuple
from .actoroutput import ActorOutputBase
from ..serialization import dump_json
from ..exception import warning


def _setter_hook_stats_actor_output_filename(self, output_filename):
    # By default, write_to_disk is False.
    # However, if user actively sets the output_filename
    # s/he most likely wants to write to disk also
    if output_filename != "" and output_filename is not None:
        self.write_to_disk = True
    return output_filename


class ActorOutputStatisticsActor(ActorOutputBase):
    """This is a hand-crafted ActorOutput specifically for the SimulationStatisticsActor."""

    # hints for IDE
    encoder: str
    output_filename: str
    write_to_disk: bool

    user_info_defaults = {
        "encoder": (
            "json",
            {
                "doc": "How should the output be encoded?",
                "allowed_values": ("json", "legacy"),
            },
        ),
        "output_filename": (
            "auto",
            {
                "doc": "Filename for the data represented by this actor output. "
                "Relative paths and filenames are taken "
                "relative to the global simulation output folder "
                "set via the Simulation.output_dir option. ",
                "setter_hook": _setter_hook_stats_actor_output_filename,
            },
        ),
        "write_to_disk": (
            False,
            {
                "doc": "Should the output be written to disk, or only kept in memory? ",
            },
        ),
    }

    default_suffix = "json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # predefine the merged_data
        self.merged_data = Box()
        self.merged_data.runs = 0
        self.merged_data.events = 0
        self.merged_data.tracks = 0
        self.merged_data.steps = 0
        self.merged_data.duration = 0
        self.merged_data.start_time = 0
        self.merged_data.stop_time = 0
        self.merged_data.sim_start_time = 0
        self.merged_data.sim_stop_time = 0
        self.merged_data.init = 0
        self.merged_data.track_types = {}
        self.merged_data.nb_threads = 1

    @property
    def pps(self):
        if self.merged_data.duration != 0:
            return int(
                self.merged_data.events / (self.merged_data.duration / g4_units.s)
            )
        else:
            return 0

    @property
    def tps(self):
        if self.merged_data.duration != 0:
            return int(
                self.merged_data.tracks / (self.merged_data.duration / g4_units.s)
            )
        else:
            return 0

    @property
    def sps(self):
        if self.merged_data.duration != 0:
            return int(
                self.merged_data.steps / (self.merged_data.duration / g4_units.s)
            )
        else:
            return 0

    def store_data(self, data, **kwargs):
        self.merged_data.update(data)

    def get_data(self, **kwargs):
        if "which" in kwargs and kwargs["which"] != "merged":
            warning(
                f"The statistics actor output only stores merged data currently. "
                f"The which={kwargs['which']} you provided will be ignored. "
            )
        # the statistics actor currently only handles merged data, so we return it
        # no input variable 'which' as in other output classes
        return self.merged_data

    def get_processed_output(self):
        d = {}
        d["runs"] = {"value": self.merged_data.runs, "unit": None}
        d["events"] = {"value": self.merged_data.events, "unit": None}
        d["tracks"] = {"value": self.merged_data.tracks, "unit": None}
        d["steps"] = {"value": self.merged_data.steps, "unit": None}
        val, unit = g4_best_unit_tuple(self.merged_data.init, "Time")
        d["init"] = {
            "value": val,
            "unit": unit,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.duration, "Time")
        d["duration"] = {
            "value": val,
            "unit": unit,
        }
        d["pps"] = {"value": self.pps, "unit": None}
        d["tps"] = {"value": self.tps, "unit": None}
        d["sps"] = {"value": self.sps, "unit": None}
        d["start_time"] = {
            "value": self.merged_data.start_time,
            "unit": None,
        }
        d["stop_time"] = {
            "value": self.merged_data.stop_time,
            "unit": None,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.sim_start_time, "Time")
        d["sim_start_time"] = {
            "value": val,
            "unit": unit,
        }
        val, unit = g4_best_unit_tuple(self.merged_data.sim_stop_time, "Time")
        d["sim_stop_time"] = {
            "value": val,
            "unit": unit,
        }
        d["threads"] = {"value": self.merged_data.nb_threads, "unit": None}
        d["arch"] = {"value": platform.system(), "unit": None}
        d["python"] = {"value": platform.python_version(), "unit": None}
        d["track_types"] = {"value": self.merged_data.track_types, "unit": None}
        return d

    def __str__(self):
        s = ""
        for k, v in self.get_processed_output().items():
            if k == "track_types":
                if len(v["value"]) > 0:
                    s += "track_types\n"
                    for t, n in v["value"].items():
                        s += f"{' ' * 24}{t}: {n}\n"
            else:
                if v["unit"] is None:
                    unit = ""
                else:
                    unit = str(v["unit"])
                s += f"{k}{' ' * (20 - len(k))}{v['value']} {unit}\n"
        # remove last line break
        return s.rstrip("\n")

    def write_data(self, **kwargs):
        """Override virtual method from base class."""
        with open(self.get_output_path(which="merged"), "w+") as f:
            if self.encoder == "json":
                dump_json(self.get_processed_output(), f, indent=4)
            else:
                f.write(self.__str__())

    def write_data_if_requested(self, **kwargs):
        if self.write_to_disk is True:
            self.write_data(**kwargs)


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
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateSimulationStatisticsActor.__init__(self, self.user_info)
        self.AddActions({"StartSimulationAction", "EndSimulationAction"})

    def __str__(self):
        s = self.user_output["stats"].__str__()
        return s

    @property
    def counts(self):
        return self.user_output.stats.merged_data

    def store_output_data(self, output_name, run_index, *data):
        raise NotImplementedError

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInput(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateSimulationStatisticsActor.StartSimulationAction(self)
        self.user_output.stats.merged_data.nb_threads = (
            self.simulation.number_of_threads
        )

    def EndSimulationAction(self):
        g4.GateSimulationStatisticsActor.EndSimulationAction(self)
        self.user_output.stats.store_data(self.GetCounts())

        if self.simulation is not None:
            sim_start = self.simulation.run_timing_intervals[0][0]
        else:
            sim_start = 0

        if self.simulation is not None:
            sim_stop = self.simulation.run_timing_intervals[-1][1]
        else:
            sim_stop = 0

        self.user_output.stats.store_data(
            {"sim_start": sim_start, "sim_stop": sim_stop}
        )
        self.user_output.stats.merged_data.sim_start_time = (
            self.simulation.run_timing_intervals[0][0]
        )
        self.user_output.stats.merged_data.sim_stop_time = (
            self.simulation.run_timing_intervals[-1][1]
        )
        self.user_output.stats.merged_data.nb_threads = (
            self.simulation.number_of_threads
        )
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
