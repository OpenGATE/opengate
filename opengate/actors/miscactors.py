import platform

import opengate_core as g4
from anytree import Node, RenderTree

from ..base import process_cls
from ..exception import fatal, warning
from .actoroutput import (
    ActorOutputBase,
    ActorOutputSingleImage,
    ActorOutputStatisticsActor,
    ActorOutputUsingDataItemContainer,
)
from .base import ActorBase
from .dataitems import DepositedChargeItemContainer

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

    def __str__(self):
        s = self.user_output["stats"].__str__()
        return s

    @property
    def counts(self):
        return self.user_output.stats.get_data(which="merged")

    def store_output_data(self, output_name, run_index, *data):
        raise NotImplementedError

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        g4.GateSimulationStatisticsActor.StartSimulationAction(self)

    def EndOfRunActionMasterThread(self, run_index):
        g4.GateSimulationStatisticsActor.EndOfRunActionMasterThread(self, run_index)
        data = dict(self.GetCountsCurrentRun())
        if self.simulation is not None:
            data["run_start"] = self.simulation.run_timing_intervals[run_index][0]
            data["run_stop"] = self.simulation.run_timing_intervals[run_index][1]
            data["nb_threads"] = self.simulation.number_of_threads
        self.user_output.stats.store_data(run_index, data)
        self.user_output.stats.write_data_if_requested(which=run_index)
        return 0

    def EndSimulationAction(self):
        g4.GateSimulationStatisticsActor.EndSimulationAction(self)
        data = dict(self.GetCounts())
        # FIXME: split-job merging needs explicit handling of run identities for
        # the statistics output. Naively summing child-local "runs" counters is
        # not meaningful. Child outputs should carry original master run indices
        # or be remapped during merge so the merged stats can reconstruct the
        # set of original runs directly from actor output data.

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
        self.user_output.stats.write_data_if_requested(which="merged")


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


class KillAccordingParticleNameActor(ActorBase, g4.GateKillAccordingParticleNameActor):
    """Actor which kills a particle according the particle name provied by the user at the exit of the
    actorified volume."""

    particles_name_to_kill: list

    user_info_defaults = {
        "particles_name_to_kill": (
            [],
            {
                "doc": "Put particles name the user wants to kill at the exit of the volume"
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.number_of_killed_particles = 0
        self.__initcpp__()
        self.list_of_volume_name = []

    def __initcpp__(self):
        g4.GateKillAccordingParticleNameActor.__init__(self, self.user_info)
        self.AddActions(
            {"PreUserTrackingAction", "SteppingAction", "EndSimulationAction"}
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
        self.number_of_killed_particles = self.GetNumberOfKilledParticles()


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
        # FIXME: Should rely on user_output_config and not call _add_user_output manually
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
        self.simulation.volume_manager.update_volume_tree_if_needed()
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


class ActorOutputDepositedChargeActor(ActorOutputUsingDataItemContainer):
    """Structured deposited-charge output with history-by-history statistics."""

    data_container_class = DepositedChargeItemContainer

    # hints for IDE
    encoder: str

    user_info_defaults = {
        "encoder": (
            "json",
            {
                "doc": "How should the output be encoded?",
                "allowed_values": ("json", "legacy"),
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        self.default_suffix = "json"
        super().__init__(*args, **kwargs)
        self.set_write_to_disk(False)
        self.set_active(True)

    @property
    def _charge_item(self):
        if self.merged_data is None:
            return None
        return self.merged_data.get_data_item_object(0)

    def resolve_and_validate_config(self, context=None):
        super().resolve_and_validate_config(context=context)
        if self.get_output_filename() not in ("", None, "auto"):
            self.set_write_to_disk(True)

    def _charge_item_of(self, which):
        container = self.get_data_container(which)
        if container is None:
            return None
        return container.get_data_item_object(0)

    def charge_statistics(self, kind="nominal", which="merged"):
        """History-by-history statistics for the merged result (which='merged')
        or for a specific run (which=run_index, requires keep_data_per_run=True).
        """
        charge_item = self._charge_item_of(which)
        if charge_item is None:
            return None
        return charge_item.statistics(kind)

    @property
    def nominal_charge_statistics(self):
        """History-by-history statistics for the merged nominal deposited charge."""
        return self.charge_statistics("nominal")

    @property
    def dynamic_charge_statistics(self):
        """History-by-history statistics for the merged dynamic deposited charge."""
        return self.charge_statistics("dynamic")

    def get_processed_output(self, which="merged"):
        charge_item = self._charge_item_of(which)
        if charge_item is None:
            return {}
        return charge_item.get_processed_output()

    def __str__(self):
        if self._charge_item is None:
            return "No data found. "
        return str(self._charge_item)

    def write_data(self, which="all", item="all", **kwargs):
        # write_data() recurses through self.write_data() for which="all", so
        # the encoder must be injected only once, not re-added on every level.
        kwargs.setdefault("encoder", self.encoder)
        super().write_data(which=which, item=item, **kwargs)


class DepositedChargeActor(ActorBase, g4.GateDepositedChargeActor):
    """Actor which accumulates the net electric charge deposited in a volume,
    defined as the sum of the charge of charged particles dying in the volume
    minus the sum of the charge of charged particles being born in it. The result is
    expressed in elementary-charge units (eplus).

        Two different quantities are accumulated:
            - Nominal deposited charge: uses the PDG charge of the particles.
            - Dynamic deposited charge: uses the effective charge of the particles, accounting for ionisation.
    """

    user_output_config = {
        "charge": {
            "actor_output_class": ActorOutputDepositedChargeActor,
        },
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateDepositedChargeActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "StartSimulationAction",
                "EndSimulationAction",
                "BeginOfRunActionMasterThread",
                "BeginOfRunAction",
                "BeginOfEventAction",
                "PreUserTrackingAction",
                "PostUserTrackingAction",
                "EndOfEventAction",
                "EndOfRunAction",
                "EndOfRunActionMasterThread",
            }
        )

    def initialize(self):
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def StartSimulationAction(self):
        # inform actor output that this simulation is starting
        for u in self.user_output.values():
            if u.get_active(item="any"):
                u.start_of_simulation()

    def EndOfRunActionMasterThread(self, run_index):
        # Hand the per-run moments to the output object. The C++ accumulators
        # are reset at the beginning of every run, so this is per-run data;
        # end_of_run() below folds it into the merged result and drops the
        # per-run container unless keep_data_per_run is set.
        self.user_output.charge.store_data(
            run_index,
            {
                "deposited_nominal_charge": self.GetDepositedNominalCharge(),
                "deposited_dynamic_charge": self.GetDepositedDynamicCharge(),
                "deposited_nominal_charge_squared": self.GetDepositedNominalChargeSquared(),
                "deposited_dynamic_charge_squared": self.GetDepositedDynamicChargeSquared(),
                "number_of_events": self.GetNumberOfEvents(),
            },
        )
        # inform actor output that this run is over
        for u in self.user_output.values():
            if u.get_active(item="all"):
                u.end_of_run(run_index)
        return 0

    def EndSimulationAction(self):
        # inform actor output that this simulation is over and write data
        for u in self.user_output.values():
            if u.get_active(item="any"):
                u.end_of_simulation()

    def __str__(self):
        return (
            f"DepositedChargeActor {self.name}:\n" + self.user_output.charge.__str__()
        )


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


class DebugActor(ActorBase, g4.GateDebugActor):
    """
    Process tracking for debugging and education purposes.

    Example usage in Python:
      debug = sim.add_actor("DebugActor", "debug")
      debug.debug_flag = True
    """

    user_info_defaults = {"debug_flag": (False, {"doc": "Test option"})}

    def __init__(self, *args, **kwargs):
        print(f"(python) DebugActor: __init__")
        ActorBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        print(f"(python) DebugActor ({self.name}) : __initcpp__")
        g4.GateDebugActor.__init__(self, self.user_info)
        print(f"(python) DebugActor ({self.name}) : AddActions")
        self.AddActions(
            {
                "BeginOfSimulationAction",
                "BeginOfRunAction",
                "PreUserTrackingAction",
                "PostUserTrackingAction",
                "BeginOfEventAction",
                "EndOfEventAction",
                "SteppingAction",
                "EndOfRunAction",
                "EndOfSimulationAction",
            }
        )

    def __getstate__(self):
        print(f"(python) DebugActor ({self.name}) : __getstate__")
        return ActorBase.__getstate__(self)

    def __setstate__(self, state):
        print(f"(python) DebugActor ({self.name}) : __setstate__")
        ActorBase.__setstate__(self, state)

    def initialize(self):
        print(f"(python) DebugActor ({self.name}) : initialize")
        ActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        self.InitializeCpp()

    def BeginOfSimulationAction(self):
        print(f"(python) DebugActor ({self.name}) : BeginOfSimulationAction")
        g4.GateDebugActor.BeginOfSimulationAction(self)

    def EndOfSimulationAction(self):
        print(f"(python) DebugActor ({self.name}) : EndOfSimulationAction")
        g4.GateDebugActor.EndOfSimulationAction(self)


process_cls(ActorOutputStatisticsActor)
process_cls(SimulationStatisticsActor)
process_cls(KillActor)
process_cls(ActorOutputDepositedChargeActor)
process_cls(DepositedChargeActor)
process_cls(ActorOutputKillAccordingProcessesActor)
process_cls(KillAccordingProcessesActor)
process_cls(KillAccordingParticleNameActor)
process_cls(ActorOutputKillNonInteractingParticleActor)
process_cls(KillNonInteractingParticleActor)
process_cls(AttenuationImageActor)
process_cls(DebugActor)
