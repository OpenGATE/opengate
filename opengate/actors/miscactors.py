from box import Box
import platform
import opengate_core as g4
from .base import ActorBase
from ..utility import g4_units
from .actoroutput import ActorOutputStatisticsActor
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
