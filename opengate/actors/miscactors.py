from box import Box
import platform
from anytree import Node, RenderTree
import opengate_core as g4
from anytree import Node, RenderTree
from .base import ActorBase
from ..utility import g4_units, g4_best_unit_tuple
from .actoroutput import ActorOutputBase
from ..serialization import dump_json
from ..exception import fatal, warning
from ..base import process_cls
from anytree import Node, RenderTree


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
        "is_rayleigh_an_interaction":(
            True,
            {
                "doc": "Specific case to be faster. If a user wants to kill all interactions which implies an energy loss, this boolean enables to not account Rayleigh process as an interaction"
            }
        )
    }

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
            {"BeginOfRunAction","BeginOfEventAction","PreUserTrackingAction", "SteppingAction","EndSimulationAction"}
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        if len(self.user_info.processes_to_kill)== 0:
            fatal("You have to select at least one process ! ")


    def EndSimulationAction(self):
        self.user_output.kill_interacting_particles.number_of_killed_particles = (
            self.number_of_killed_particles
        )

    def __str__(self):
        s = self.user_output["kill_non_interacting_particles"].__str__()
        return s

class KillActor(ActorBase, g4.GateKillActor):
    """
    Actor which kill a particle entering in a volume with the following attached actor.

    """

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


class ActorOutputKillNonInteractingParticleActor(ActorOutputBase):

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


class KillNonInteractingParticleActor(
    ActorBase, g4.GateKillNonInteractingParticleActor
):
    """
    If a particle, not generated or generated within the volume at which our actor is attached, crosses the volume
    without interaction, the particle is killed. Warning : this actor being based on energy measurement, Rayleigh photon
    may not be killed.
    """

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self._add_user_output(
            ActorOutputKillNonInteractingParticleActor, "kill_non_interacting_particles"
        )
        self.__initcpp__()
        self.list_of_volume_name = []
        self.number_of_killed_particles = 0

    def __initcpp__(self):
        g4.GateKillNonInteractingParticleActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "StartSimulationAction",
                "PreUserTrackingAction",
                "SteppingAction",
                "EndOfSimulationAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        volume_tree = self.simulation.volume_manager.get_volume_tree()
        dico_of_volume_tree = {}
        for pre, _, node in RenderTree(volume_tree):
            dico_of_volume_tree[str(node.name)] = node
        volume_name = self.user_info.attached_to
        while volume_name != "world":
            node = dico_of_volume_tree[volume_name]
            volume_name = node.mother
            self.list_of_volume_name.append(volume_name)
        self.fListOfVolumeAncestor = self.list_of_volume_name

    def EndSimulationAction(self):
        self.user_output.kill_non_interacting_particles.number_of_killed_particles = (
            self.number_of_killed_particles
        )

    def __str__(self):
        s = self.user_output["kill_non_interacting_particles"].__str__()
        return s


def _setter_hook_particles(self, value):
    if isinstance(value, str):
        return [value]
    else:
        return list(value)


class SplittingActorBase(ActorBase):
    """
    Actors based on the G4GenericBiasing class of GEANT4. This class provides tools to interact with GEANT4 processes
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
    """
    This splitting actor enables process-based splitting specifically for Compton interactions. Each time a Compton
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


class LastVertexInteractionSplittingActor(
    ActorBase, g4.GateLastVertexInteractionSplittingActor
):
    """This splitting actor proposes an interaction splitting at the last particle vertex before the exit
     of the biased volume.  This actor can be usefull for application where collimation are important,
    such as in medical LINAC (Linear Accelerator) simulations or radiation shielding.
    """


    # hints for IDE
    splitting_factor: int
    angular_kill: bool
    max_theta: float
    vector_director: list
    rotation_vector_director: bool
    batch_size:int
    nb_of_max_batch_per_event:int


    user_info_defaults = {
        "splitting_factor": (
            1,
            {
                "doc": "Defines the number of particles exiting at each split process. Unlike other split actors, this splitting factor counts particles that actually exit, not just those generated.",
            },
        ),
        "angular_kill": (
            False,
            {
                "doc": "If enabled, particles with momentum outside a specified angular range are killed.",
            },
        ),
        "max_theta": (
            90 * g4_units.deg,
            {
                "doc": "Defines the maximum angle (in degrees) from a central axis within which particles are retained. Particles with momentum beyond this angle are removed. The angular range spans from 0 to max_theta, measured from the vector_director",
            },
        ),
        "vector_director": (
            [0, 0, 1],
            {
                "doc": "Specifies the reference direction vector from which max_theta is measured. Particles’ angular range is calculated based on this direction.",
            },
        ),
        "rotation_vector_director": (
            False,
            {
                "doc": "If enabled, the vector_director rotates in alignment with any rotation applied to the biased volume attached to this actor.",
            },
        ),
        "batch_size": (
            1,
            {
                "doc": "Defines a batch of number of processes to regenerate. The optimal value depends on the collimation setup; for example, a batch_size of 10 works well for LINAC head configurations.",
            },
        ),
        "nb_of_max_batch_per_event": (
            500,
            {
                "doc": "Defines a maximum number of attempt to enable the particles to exit. Useful to avoid an important loss of time for extremely rare events",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()
        self.list_of_volume_name = []

    def __initcpp__(self):
        g4.GateLastVertexInteractionSplittingActor.__init__(self, {"name": self.name})
        self.AddActions(
            {
                "BeginOfRunAction",
                "BeginOfEventAction",
                "PreUserTrackingAction",
                "SteppingAction",
                "PostUserTrackingAction",
                "EndOfEventAction",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()
        volume_tree = self.simulation.volume_manager.get_volume_tree()
        dico_of_volume_tree = {}
        for pre, _, node in RenderTree(volume_tree):
            dico_of_volume_tree[str(node.name)] = node
        volume_name = self.user_info.attached_to
        while volume_name != "world":
            node = dico_of_volume_tree[volume_name]
            volume_name = node.mother
            self.list_of_volume_name.append(volume_name)
        self.fListOfVolumeAncestor = self.list_of_volume_name


class BremSplittingActor(SplittingActorBase, g4.GateBOptrBremSplittingActor):
    """
    This splitting actor enables process-based splitting specifically for bremsstrahlung process. Each time a Brem
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
process_cls(KillAccordingProcessesActor)
process_cls(LastVertexInteractionSplittingActor)
process_cls(KillNonInteractingParticleActor)
process_cls(SplittingActorBase)
process_cls(ComptSplittingActor)
process_cls(BremSplittingActor)
