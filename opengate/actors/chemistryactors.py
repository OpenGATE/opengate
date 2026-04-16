from box import Box
import opengate_core as g4

from .base import ActorBase
from .actoroutput import ActorOutputBase, ActorOutputUsingDataItemContainer
from .dataitems import SingleTimeCountSeries
from .chemistrycounters import (
    CounterBase,
    MoleculeCounterBase,
    chemistry_counter_types,
)
from ..serialization import dump_json
from ..exception import warning, fatal
from ..base import process_cls, create_gate_object_from_dict
from ..utility import g4_units


class ChemistryActorBase(ActorBase):
    """
    Base class for chemistry-aware actors.

    The class itself is intentionally light: chemistry participation is mainly
    implemented through the C++ GateVChemistryActor side, while Python uses the
    type for configuration, validation and actor discovery.
    """

    counter_config = {}
    user_output_config = {}

    user_info_defaults = {
        "confine_chemistry_to_volume": (
            True,
            {
                "doc": "If True, chemistry tracks starting outside the attached volume subtree are killed before chemistry processing.",
            },
        ),
        "chemistry_list_name": (
            None,
            {
                "doc": "Chemistry list requested by this actor. ",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        ActorBase.__init__(self, *args, **kwargs)
        self.required_molecule_counter_manager_policy: dict[str, bool | None] = {
            "reset_counters_before_event": None,
            "reset_counters_before_run": None,
            "reset_master_counter_with_workers": None,
            "accumulate_counter_into_master": None,
        }
        self.counters = Box()
        self._instantiate_configured_counters()

    def close(self):
        for counter in self.counters.values():
            counter.close()
        super().close()

    def initialize(self):
        ActorBase.initialize(self)
        for counter in self.counters.values():
            counter.simulation = self.simulation
            counter.actor = self
            if counter.active:
                counter.initialize()

    def _create_counter(self, counter, name=None, **kwargs):
        new_counter = None
        if isinstance(counter, str):
            if name is None:
                fatal("You must provide a name for the counter.")
            try:
                counter_class = chemistry_counter_types[counter]
            except KeyError:
                fatal(
                    f"Unknown chemistry counter type '{counter}'. "
                    f"Known types are: {list(chemistry_counter_types.keys())}"
                )
            new_counter = counter_class(name=name, simulation=self.simulation, **kwargs)
        elif isinstance(counter, type):
            if not issubclass(counter, CounterBase):
                fatal(
                    f"Counter class '{counter}' does not inherit from CounterBase."
                )
            if name is None:
                fatal("You must provide a name for the counter.")
            new_counter = counter(name=name, simulation=self.simulation, **kwargs)
        elif isinstance(counter, CounterBase):
            if kwargs:
                fatal(
                    "Cannot provide keyword configuration when passing an existing counter object."
                )
            new_counter = counter
        else:
            fatal(
                "You need to either provide a counter type and name, a counter class and name, "
                "or a counter object."
            )
        return new_counter

    def _attach_counter(self, counter_name, counter):
        if counter_name in self.counters:
            fatal(
                f"The chemistry counter named {counter_name} already exists "
                f"in actor '{self.name}'. Existing counter names are: {list(self.counters.keys())}"
            )
        self.counters[counter_name] = counter
        counter.simulation = self.simulation
        counter.actor = self

    def _instantiate_counter_from_config(self, counter_name, counter_spec):
        try:
            counter_class = counter_spec["counter_class"]
        except KeyError:
            fatal(
                f"Counter config for '{counter_name}' in actor '{self.name}' "
                "does not define 'counter_class'."
            )
        output_name = counter_spec.get("output_name", counter_name)
        counter_kwargs = dict(counter_spec.get("counter_kwargs", {}))
        counter_kwargs["output_name"] = output_name
        counter = self._create_counter(
            counter_class,
            name=counter_name,
            **counter_kwargs,
        )
        self._attach_counter(counter_name, counter)

    def _instantiate_configured_counters(self):
        for counter_name, counter_spec in self.counter_config.items():
            self._instantiate_counter_from_config(counter_name, counter_spec)

    @classmethod
    def _make_counter_output_config(cls):
        output_config = {}
        for counter_name, counter_spec in cls.counter_config.items():
            output_name = counter_spec.get("output_name", counter_name)
            if output_name in cls.user_output_config:
                fatal(
                    f"Chemistry actor class '{cls.__name__}' declares counter '{counter_name}' "
                    f"with output_name '{output_name}', but this output name already exists "
                    "in user_output_config."
                )
            output_config[output_name] = {
                "actor_output_class": ActorOutputChemicalCounter,
                "active": True,
                "write_to_disk": False,
            }
        return output_config

    @classmethod
    def _process_user_output_config(cls):
        original_output_config = cls.user_output_config
        cls.user_output_config = dict(original_output_config)
        cls.user_output_config.update(cls._make_counter_output_config())
        try:
            super()._process_user_output_config()
        finally:
            cls.user_output_config = original_output_config

    def _reconstruct_counters_from_dictionary(self, counter_dicts):
        counters = Box()
        for counter_dict in counter_dicts.values():
            counter = create_gate_object_from_dict(counter_dict)
            if not isinstance(counter, CounterBase):
                fatal(
                    f"Expected a serialized CounterBase, but reconstructed {type(counter).__name__}."
                )
            counter.simulation = self.simulation
            counter.actor = self
            counter.from_dictionary(counter_dict)
            counters[counter.name] = counter
        return counters

    def to_dictionary(self):
        d = super().to_dictionary()
        d["counters"] = {
            counter_name: counter.to_dictionary()
            for counter_name, counter in self.counters.items()
        }
        return d

    def from_dictionary(self, d):
        super().from_dictionary(d)
        self.counters = self._reconstruct_counters_from_dictionary(d.get("counters", {}))

    def _store_counter_results(self, which="merged"):
        for counter in self.counters.values():
            if counter.g4_counter_id is not None and counter.output_name is not None:
                self.user_output[counter.output_name].store_data(
                    which, counter._collect_results()
                )


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


class ActorOutputChemicalCounter(ActorOutputUsingDataItemContainer):
    data_container_class = SingleTimeCountSeries

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

    counter_config = {
        "molecule_counter": {
            "counter_class": "BuiltinMoleculeCounter",
            "output_name": "molecule_counter",
            "counter_kwargs": {
                "time_comparer": {
                    "method": "fixed_precision",
                    "precision": 1 * g4_units.ps,
                },
                "ignored_molecules": ["H2O"],
            },
        },
        "reaction_counter": {
            "counter_class": "BuiltinReactionCounter",
            "output_name": "reaction_counter",
            "counter_kwargs": {
                "time_comparer": {
                    "method": "fixed_precision",
                    "precision": 1 * g4_units.ps,
                },
            },
        },
    }

    user_info_defaults = {
        "track_only_primary": (
            True,
            {
                "doc": "Apply the chem6-like energy-loss logic only to the primary track."
            },
        ),
        "primary_pdg_code": (
            11,
            {"doc": "PDG code of the primary particle for the chem6-like logic."},
        ),
        "energy_loss_min": (
            -1.0,
            {
                "doc": "Kill the tracked primary when accumulated energy loss exceeds this value. Negative disables it."
            },
        ),
        "energy_loss_max": (
            -1.0,
            {
                "doc": "Abort the event when accumulated energy loss exceeds this value. Negative disables it."
            },
        ),
        "min_kinetic_energy": (
            0.0,
            {
                "doc": "Kill the tracked primary when its kinetic energy falls below this value."
            },
        ),
        "let_cutoff": (
            1e30,
            {
                "doc": "Restricted LET cutoff energy. Secondary kinetic energies below this threshold are added to the event energy deposit."
            },
        ),
        "times_to_record": (
            [],
            {
                "doc": "Explicit chemistry times at which species numbers and G values should be recorded."
            },
        ),
        "number_of_time_bins": (
            10,
            {
                "doc": "If > 0 and times_to_record is empty, generate logarithmically spaced chemistry scoring times like chem6."
            },
        ),
    }

    user_output_config = {
        "results": {
            "actor_output_class": ActorOutputChemicalStageActor,
        },
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("track_structure_em_physics", "G4EmDNAPhysics_option2")
        ChemistryActorBase.__init__(self, *args, **kwargs)
        self.required_molecule_counter_manager_policy.update(
            {
                "reset_counters_before_event": True,
                "reset_counters_before_run": True,
                "accumulate_counter_into_master": False,
            }
        )
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateChemicalStageActor.__init__(self, self.user_info)
        self.AddActions(
            {
                "StartSimulationAction",
                "BeginOfEventAction",
                "SteppingAction",
                "NewStage",
                "InitializeChemistryTracking",
                "AppendChemistryStep",
                "StartChemistryTracking",
                "EndChemistryTracking",
                "FinalizeChemistryTracking",
                "StartChemistryProcessing",
                "PreChemistryTimeStepAction",
                "PostChemistryTimeStepAction",
                "ChemistryReactionAction",
                "EndOfEventAction",
                "EndChemistryProcessing",
                "EndSimulationAction",
            }
        )

    def initialize(self):
        ChemistryActorBase.initialize(self)
        self.InitializeUserInfo(self.user_info)
        molecule_counters = [
            counter
            for counter in self.counters.values()
            if isinstance(counter, MoleculeCounterBase) and counter.g4_counter_id is not None
        ]
        if len(molecule_counters) > 1:
            fatal(
                f"ChemicalStageActor '{self.name}' currently supports at most one molecule counter "
                "for its built-in C++ species sampling path."
            )
        if len(molecule_counters) == 1:
            self.SetMoleculeCounterId(molecule_counters[0].g4_counter_id)
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
            "times_to_record": self.GetRecordedTimes(),
        }
        self.user_output.results.store_data(data)
        self._store_counter_results("merged")


process_cls(ChemistryActorBase)
process_cls(ActorOutputChemicalStageActor)
process_cls(ActorOutputChemicalCounter)
process_cls(ChemicalStageActor)
