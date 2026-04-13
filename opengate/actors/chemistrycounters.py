import opengate_core as g4

from ..base import GateObject, process_cls
from ..exception import fatal


class CounterBase(GateObject):
    user_info_defaults = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = None
        self.g4_counter_id = None

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["actor"] = None
        state_dict["g4_counter_id"] = None
        return state_dict

    def __setstate__(self, state):
        super().__setstate__(state)
        self.actor = None
        self.g4_counter_id = None

    def close(self):
        self.g4_counter_id = None
        self.actor = None
        super().close()

    def initialize(self):
        fatal(
            f"Counter class {type(self).__name__} does not implement initialize()."
        )

    def get_results(self):
        fatal(
            f"Counter class {type(self).__name__} does not implement get_results()."
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
            ignored_molecules.update(available_molecules.difference(considered_molecules))

        for molecule_name in ignored_molecules:
            self.IgnoreMolecule(molecule_name)
        self.Initialize()
        manager = g4.G4MoleculeCounterManager.Instance()
        self.g4_counter_id = manager.RegisterMoleculeCounter(self)


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


chemistry_counter_types = {
    "BuiltinMoleculeCounter": BuiltinMoleculeCounter,
    "BuiltinReactionCounter": BuiltinReactionCounter,
}


process_cls(CounterBase)
process_cls(MoleculeCounterBase)
process_cls(ReactionCounterBase)
process_cls(BuiltinMoleculeCounter)
process_cls(BuiltinReactionCounter)
