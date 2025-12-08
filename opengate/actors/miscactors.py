from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units, g4_best_unit_tuple
from .actoroutput import ActorOutputBase, ActorOutputSingleImage
from ..serialization import dump_json
from ..exception import fatal, warning
from ..base import process_cls

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
        "active": (
            True,
            {"doc": "This actor is always active. ", "read_only": True},
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
        self.InitializeUserInfo(self.user_info)
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
    user_output_config = {
        "kill_according_processes": {
            "actor_output_class": ActorOutputKillAccordingProcessesActor,
        },
    }

    """
    If a particle, not generated or generated within the volume at which our actor is attached, crosses the volume
    without interaction, the particle is killed.
    """

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
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
        self.user_output.kill_according_processes.number_of_killed_particles = (
            self.number_of_killed_particles
        )

    def __str__(self):
        s = self.user_output["kill_according_processes"].__str__()
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


class AttenuationImageActor(ActorBase, g4.GateAttenuationImageActor):
    """
    This actor generates an attenuation image for a simulation run.
    The output is a single image volume in cm^-1

    - image_volume: Input volume from which the attenuation map is generated.
    - energy: The energy level for which to generate the attenuation image.
    - database: The database source for attenuation coefficients, either 'EPDL' or 'NIST'.
    """

    # IDE hints
    image_volume = str
    energy = float
    database = str

    user_info_defaults = {
        "image_volume": (  # FIXME name or not name
            None,
            {
                "doc": "Input ImageVolume for which the attenuation map is generated.",
            },
        ),
        "energy": (
            None,
            {"doc": "The energy level for which to generate the attenuation image"},
        ),
        "database": (
            "EPDL",
            {
                "doc": "The database source for attenuation coefficients, either 'EPDL' or 'NIST'",
                "allowed_values": ("EPDL", "NIST"),
            },
        ),
    }

    user_output_config = {
        "attenuation_image": {
            "actor_output_class": ActorOutputSingleImage,
            "active": True,
            "write_to_disk": True,
            "keep_data_in_memory": True,
            "keep_data_per_run": True,
        },
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateAttenuationImageActor.__init__(self, self.user_info)
        self.AddActions({"BeginOfRunAction"})

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def BeginOfRunAction(self, run):
        # the attenuation image is created during the first run only
        if run.GetRunID() != 0:
            return
        mu_image = self.image_volume.create_attenuation_image(
            self.database, self.energy
        )
        self.user_output.attenuation_image.store_data("merged", mu_image)
        self.user_output.attenuation_image.end_of_simulation()


process_cls(ActorOutputStatisticsActor)
process_cls(SimulationStatisticsActor)
process_cls(KillActor)
process_cls(ActorOutputKillAccordingProcessesActor)
process_cls(KillAccordingProcessesActor)
process_cls(AttenuationImageActor)
