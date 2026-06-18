import re

import numpy as np
import opengate_core as g4

from ..base import GateObject, process_cls
from ..chemistry import TrackedChemicalReaction
from ..exception import fatal

TIME_COUNT_DTYPE = np.dtype([("time", np.float64), ("count", np.int64)])


def _make_time_count_series(times, counts):
    if len(times) != len(counts):
        fatal(
            f"Implementation error: inconsistent time/count series lengths "
            f"({len(times)} vs {len(counts)})."
        )
    output = np.empty(len(times), dtype=TIME_COUNT_DTYPE)
    output["time"] = times
    output["count"] = counts
    return output


def _sanitize_counter_key(label):
    sanitized = re.sub(r"[^0-9A-Za-z]+", "_", label).strip("_")
    if not sanitized:
        sanitized = "unnamed"
    return sanitized


def _make_unique_key(preferred_key, existing_keys, fallback_suffix):
    if preferred_key not in existing_keys:
        return preferred_key
    unique_key = f"{preferred_key}_{fallback_suffix}"
    if unique_key not in existing_keys:
        return unique_key
    i = 1
    while f"{unique_key}_{i}" in existing_keys:
        i += 1
    return f"{unique_key}_{i}"


def _format_reaction_label(reaction):
    reactant_1 = reaction.GetReactant1()
    reactant_2 = reaction.GetReactant2()
    product_names = [str(product.GetName()) for product in reaction.GetProducts()]
    left = f"{str(reactant_1.GetName())}_{str(reactant_2.GetName())}"
    if len(product_names) > 0:
        right = "_".join(product_names)
    else:
        right = "no_products"
    return _sanitize_counter_key(f"{left}_to_{right}")


class CounterBase(GateObject):
    user_info_defaults = {
        "output_name": (
            None,
            {
                "doc": "Name of the actor output associated with this counter.",
                "read_only": True,
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = None
        self.g4_counter_id = None
        self.initialized = False

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["actor"] = None
        state_dict["g4_counter_id"] = None
        state_dict["initialized"] = False
        return state_dict

    def __setstate__(self, state):
        super().__setstate__(state)
        self.actor = None
        self.g4_counter_id = None
        self.initialized = False

    def close(self):
        self.g4_counter_id = None
        self.actor = None
        self.initialized = False
        super().close()

    def initialize(self):
        fatal(f"Counter class {type(self).__name__} does not implement initialize().")

    def _collect_results(self):
        fatal(
            f"Counter class {type(self).__name__} does not implement _collect_results()."
        )

    @property
    def active(self):
        if self.actor is None:
            fatal(
                f"Counter '{self.name}' is not attached to an actor, so its active state "
                "cannot be resolved."
            )
        if self.output_name is None:
            fatal(f"Counter '{self.name}' is not associated with any actor output.")
        try:
            return self.actor.user_output[self.output_name].get_active(item="any")
        except KeyError:
            fatal(
                f"Counter '{self.name}' expects actor output '{self.output_name}', "
                f"but actor '{self.actor.name}' does not define it."
            )

    @active.setter
    def active(self, value):
        if self.actor is None:
            fatal(
                f"Counter '{self.name}' is not attached to an actor, so its active state "
                "cannot be changed."
            )
        if self.output_name is None:
            fatal(f"Counter '{self.name}' is not associated with any actor output.")
        try:
            self.actor.user_output[self.output_name].set_active(value, item="all")
        except KeyError:
            fatal(
                f"Counter '{self.name}' expects actor output '{self.output_name}', "
                f"but actor '{self.actor.name}' does not define it."
            )

    def _create_time_comparer(self, config):
        if not config:
            return None
        method = config.get("method", "fixed_precision")
        if method == "fixed_precision":
            try:
                precision = config["precision"]
            except KeyError:
                fatal(
                    f"Counter '{self.name}' requests a fixed-precision time comparer "
                    f"but did not provide a 'precision' entry."
                )
            return g4.G4MoleculeCounterTimeComparer.CreateWithFixedPrecision(precision)
        fatal(
            f"Unsupported molecule-counter time comparer method '{method}' "
            f"in counter '{self.name}'."
        )

    def _configure_counter_common(self):
        time_comparer = self._create_time_comparer(self.time_comparer)
        if time_comparer is not None:
            self.SetTimeComparer(time_comparer)
        if self.verbose is not None:
            self.SetVerbose(self.verbose)
        if self.check_time_consistency_with_scheduler is not None:
            self.SetCheckTimeConsistencyWithScheduler(
                self.check_time_consistency_with_scheduler
            )
        if self.check_recorded_time_consistency is not None:
            self.SetCheckRecordedTimeConsistency(self.check_recorded_time_consistency)
        if self.active_lower_bound is not None:
            self.SetActiveLowerBound(
                self.active_lower_bound["time"],
                self.active_lower_bound.get("inclusive", True),
            )
        if self.active_upper_bound is not None:
            self.SetActiveUpperBound(
                self.active_upper_bound["time"],
                self.active_upper_bound.get("inclusive", True),
            )


class MoleculeCounterBase(CounterBase):
    user_info_defaults = {
        "time_comparer": (
            None,
            {
                "doc": "Optional time comparer configuration for the built-in G4 molecule counter.",
            },
        ),
        "verbose": (
            None,
            {"doc": "Optional verbosity for the underlying Geant4 counter."},
        ),
        "check_time_consistency_with_scheduler": (
            None,
            {
                "doc": "If set, forward this consistency check flag to the Geant4 counter.",
            },
        ),
        "check_recorded_time_consistency": (
            None,
            {
                "doc": "If set, forward this recorded-time consistency flag to the Geant4 counter.",
            },
        ),
        "active_lower_bound": (
            None,
            {"doc": "Optional lower active time bound configuration."},
        ),
        "active_upper_bound": (
            None,
            {"doc": "Optional upper active time bound configuration."},
        ),
        "ignored_molecules": (
            [],
            {
                "doc": "List of molecule names ignored by the Geant4 molecule counter.",
            },
        ),
        "consider_molecules": (
            "all",
            {
                "doc": "Which molecules should be considered by this counter. Use 'all' or provide a list of molecule names.",
            },
        ),
    }


class ReactionCounterBase(CounterBase):
    user_info_defaults = {
        "time_comparer": (
            None,
            {
                "doc": "Optional time comparer configuration for the built-in G4 reaction counter.",
            },
        ),
        "verbose": (
            None,
            {"doc": "Optional verbosity for the underlying Geant4 counter."},
        ),
        "check_time_consistency_with_scheduler": (
            None,
            {
                "doc": "If set, forward this consistency check flag to the Geant4 counter.",
            },
        ),
        "check_recorded_time_consistency": (
            None,
            {
                "doc": "If set, forward this recorded-time consistency flag to the Geant4 counter.",
            },
        ),
        "active_lower_bound": (
            None,
            {"doc": "Optional lower active time bound configuration."},
        ),
        "active_upper_bound": (
            None,
            {"doc": "Optional upper active time bound configuration."},
        ),
    }


class BuiltinMoleculeCounter(MoleculeCounterBase, g4.G4MoleculeCounter):
    def __init__(self, *args, **kwargs):
        MoleculeCounterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.G4MoleculeCounter.__init__(self, self.name)

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def initialize(self):
        self._configure_counter_common()
        ignored_molecules = set(self.ignored_molecules)

        if isinstance(self.consider_molecules, str):
            if self.consider_molecules != "all":
                considered_molecules = {self.consider_molecules}
            else:
                considered_molecules = None
        else:
            considered_molecules = set(self.consider_molecules)

        if considered_molecules is None:
            self.RegisterAll()
        else:
            overlap = considered_molecules.intersection(ignored_molecules)
            if overlap:
                fatal(
                    f"Molecule counter '{self.name}' defines the same molecules in "
                    f"consider_molecules and ignored_molecules: {sorted(overlap)}"
                )
            available_molecules = set(
                g4.G4MoleculeTable.Instance().GetAllMoleculeNames()
            )
            unknown_molecules = considered_molecules.difference(available_molecules)
            if unknown_molecules:
                fatal(
                    f"Molecule counter '{self.name}' requested unknown molecules in "
                    f"consider_molecules: {sorted(unknown_molecules)}. "
                    f"Known molecule names are: {sorted(available_molecules)}"
                )
            ignored_molecules.update(
                available_molecules.difference(considered_molecules)
            )

        for molecule_name in ignored_molecules:
            self.IgnoreMolecule(molecule_name)
        self.Initialize()
        manager = g4.G4MoleculeCounterManager.Instance()
        self.g4_counter_id = manager.RegisterMoleculeCounter(self)

    def _collect_results(self):
        times = sorted(self.GetRecordedTimes())
        results = {}
        for molecule in self.GetRecordedMolecules():
            molecule_name = molecule.GetName()
            counts = self.GetNbMoleculesAtTimes(molecule, times)
            results[molecule_name] = _make_time_count_series(times, counts)
        return results


class BuiltinReactionCounter(ReactionCounterBase, g4.G4MoleculeReactionCounter):
    def __init__(self, *args, **kwargs):
        ReactionCounterBase.__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.G4MoleculeReactionCounter.__init__(self, self.name)

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def initialize(self):
        self._configure_counter_common()
        self.Initialize()
        manager = g4.G4MoleculeCounterManager.Instance()
        self.g4_counter_id = manager.RegisterReactionCounter(self)

    def _collect_results(self):
        times = sorted(self.GetRecordedTimes())
        results = {}
        for reaction in self.GetRecordedReactions():
            preferred_key = _format_reaction_label(reaction)
            reaction_key = _make_unique_key(
                preferred_key, results.keys(), reaction.GetReactionID()
            )
            counts = self.GetNbReactionsAtTimes(reaction, times)
            results[reaction_key] = _make_time_count_series(times, counts)
        return results


class ConfiguredReactionCounter(CounterBase):
    # Temporary implementation note:
    # This counter currently relies on ChemicalCountingActor-owned reaction
    # callback accumulation in C++ rather than being backed by its own proper
    # concrete reaction-counter class. That keeps the implementation simple and
    # robust enough for testing, but it should eventually be refactored into a
    # first-class counter implementation parallel to BuiltinReactionCounter.
    user_info_defaults = {
        "tracked_reactions": (
            [],
            {
                "doc": "List of tracked chemistry reaction signatures.",
            },
        ),
        "record_time_series": (
            True,
            {
                "doc": "If True, store cumulative counts versus chemistry time. If False, keep only the total count in a single-point series.",
            },
        ),
    }

    def _coerce_tracked_reaction(self, reaction):
        if isinstance(reaction, TrackedChemicalReaction):
            return reaction
        if isinstance(reaction, dict):
            return TrackedChemicalReaction(**reaction)
        fatal(
            f"ConfiguredReactionCounter '{self.name}' expects tracked_reactions "
            f"to contain TrackedChemicalReaction objects or dictionaries, got {type(reaction).__name__}."
        )

    def initialize(self):
        if self.actor is None:
            fatal(
                f"Configured reaction counter '{self.name}' is not attached to an actor."
            )
        if not hasattr(self.actor, "RegisterConfiguredReactionCounter"):
            fatal(
                f"Configured reaction counter '{self.name}' requires an actor exposing "
                "RegisterConfiguredReactionCounter(), but the attached actor does not."
            )
        if len(self.tracked_reactions) == 0:
            fatal(
                f"Configured reaction counter '{self.name}' requires at least one tracked reaction."
            )

        molecule_table = g4.G4MoleculeTable.Instance()
        normalized_reactions = []
        for tracked_reaction in self.tracked_reactions:
            tracked_reaction = self._coerce_tracked_reaction(tracked_reaction)
            runtime_reactants = []
            for reactant_name in (
                tracked_reaction.reactant_a,
                tracked_reaction.reactant_b,
            ):
                conf = molecule_table.GetConfiguration(reactant_name, False)
                if conf is None:
                    fatal(
                        f"Configured reaction counter '{self.name}' references unknown reactant "
                        f"'{reactant_name}' in tracked reaction '{tracked_reaction.name}'."
                    )
                runtime_reactants.append(str(conf.GetName()))
            runtime_products = []
            for product_name in tracked_reaction.products:
                conf = molecule_table.GetConfiguration(product_name, False)
                if conf is None:
                    fatal(
                        f"Configured reaction counter '{self.name}' references unknown product "
                        f"'{product_name}' in tracked reaction '{tracked_reaction.name}'."
                    )
                runtime_products.append(str(conf.GetName()))
            normalized_reactions.append(
                {
                    "name": tracked_reaction.name,
                    "reactant_a": runtime_reactants[0],
                    "reactant_b": runtime_reactants[1],
                    "products": runtime_products,
                }
            )

        self.actor.RegisterConfiguredReactionCounter(
            self.name, normalized_reactions, self.record_time_series
        )

    def _collect_results(self):
        if self.actor is None:
            fatal(
                f"Configured reaction counter '{self.name}' is not attached to an actor."
            )
        raw_results = self.actor.GetConfiguredReactionCounterResults(self.name)
        results = {}
        for reaction_name, entry in raw_results.items():
            times = list(entry["times"])
            counts = list(entry["counts"])
            results[str(reaction_name)] = _make_time_count_series(times, counts)
        return results


class ConfiguredSpeciesCounter(CounterBase):
    user_info_defaults = {
        "tracked_species": (
            [],
            {
                "doc": "List of chemistry species names whose appearance should be counted.",
            },
        ),
        "record_time_series": (
            True,
            {
                "doc": "If True, store cumulative appearance counts versus chemistry time. If False, keep only the total count in a single-point series.",
            },
        ),
    }

    def initialize(self):
        if self.actor is None:
            fatal(
                f"Configured species counter '{self.name}' is not attached to an actor."
            )
        if not hasattr(self.actor, "RegisterConfiguredSpeciesCounter"):
            fatal(
                f"Configured species counter '{self.name}' requires an actor exposing "
                "RegisterConfiguredSpeciesCounter(), but the attached actor does not."
            )
        if len(self.tracked_species) == 0:
            fatal(
                f"Configured species counter '{self.name}' requires at least one tracked species."
            )

        molecule_table = g4.G4MoleculeTable.Instance()
        available_molecules = set(molecule_table.GetAllMoleculeNames())
        normalized_species = []
        for species_name in self.tracked_species:
            conf = molecule_table.GetConfiguration(species_name, False)
            if conf is None and species_name not in available_molecules:
                fatal(
                    f"Configured species counter '{self.name}' references unknown species "
                    f"'{species_name}'."
                )
            normalized_species.append(
                {
                    "name": str(species_name),
                    "runtime_name": (
                        str(conf.GetName()) if conf is not None else str(species_name)
                    ),
                }
            )

        self.actor.RegisterConfiguredSpeciesCounter(
            self.name, normalized_species, self.record_time_series
        )

    def _collect_results(self):
        if self.actor is None:
            fatal(
                f"Configured species counter '{self.name}' is not attached to an actor."
            )
        raw_results = self.actor.GetConfiguredSpeciesCounterResults(self.name)
        results = {}
        for species_name, entry in raw_results.items():
            times = list(entry["times"])
            counts = list(entry["counts"])
            results[str(species_name)] = _make_time_count_series(times, counts)
        return results


chemistry_counter_types = {
    "BuiltinMoleculeCounter": BuiltinMoleculeCounter,
    "BuiltinReactionCounter": BuiltinReactionCounter,
    "ConfiguredReactionCounter": ConfiguredReactionCounter,
    "ConfiguredSpeciesCounter": ConfiguredSpeciesCounter,
}


process_cls(CounterBase)
process_cls(MoleculeCounterBase)
process_cls(ReactionCounterBase)
process_cls(BuiltinMoleculeCounter)
process_cls(BuiltinReactionCounter)
process_cls(ConfiguredReactionCounter)
process_cls(ConfiguredSpeciesCounter)
