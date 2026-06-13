from .base import GateObject, process_cls, create_gate_object_from_dict
from .utility import g4_units, fatal
from .decorators import requires_fatal
from .definitions import __world_name__

import opengate_core as g4
from opengate_core import G4MoleculeTable, G4VUserChemistryList

from box import Box
import numpy as np
import re

g = g4_units.g
m = g4_units.m
mole = g4_units.mole
nm = g4_units.nm
s = g4_units.s

known_g4_chemistry_list_names = (
    "G4EmDNAChemistry",
    "G4EmDNAChemistry_option1",
    "G4EmDNAChemistry_option2",
    "G4EmDNAChemistry_option3",
)


default_chemical_species = {
    "e_aq": {
        "name": "e_aq",
        "molecular_mass": 0.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "OH": {
        "name": "OH",
        "molecular_mass": 17.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "H": {
        "name": "H",
        "molecular_mass": 1.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "H2": {
        "name": "H2",
        "molecular_mass": 2.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "H2O2": {
        "name": "H2O2",
        "molecular_mass": 34.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "HO2": {
        "name": "HO2",
        "molecular_mass": 33.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
    "O2": {
        "name": "O2",
        "molecular_mass": 32.0 * g / mole,
        "charge": 0,
        "electronic_level": 0,
        "diffusion_radius": 0.0 * nm,
        "diffusion_coefficient": None,
    },
}


class ChemistryWorldComponent(GateObject):
    user_info_defaults = {
        "species": (
            None,
            {
                "doc": "Name of the chemistry-world component species.",
                "type": "str",
            },
        ),
        "concentration": (
            None,
            {
                "doc": "Initial concentration of the species in the chemistry world.",
            },
        ),
    }


class ScavengerReaction(GateObject):
    user_info_defaults = {
        "tracked_molecule": (
            None,
            {
                "doc": "Name of the mobile species to which the scavenger process is attached.",
                "type": "str",
            },
        ),
        "scavenger": (
            None,
            {
                "doc": "Name of the background scavenger species defined in the chemistry world.",
                "type": "str",
            },
        ),
        "products": (
            [],
            {
                "doc": "Product species created by the scavenger reaction.",
                "type": "list_of_str",
            },
        ),
        "rate_constant": (
            None,
            {
                "doc": "Observed reaction rate constant for the scavenger reaction.",
            },
        ),
        "reaction_type": (
            0,
            {
                "doc": "Geant4-DNA reaction type identifier.",
                "type": "int",
            },
        ),
    }

    @property
    def key(self):
        return (
            self.tracked_molecule,
            self.scavenger,
            tuple(self.products),
            self.reaction_type,
        )


class ChemistryWorld(GateObject):
    user_info_defaults = {
        "translation": (
            [0.0, 0.0, 0.0],
            {
                "doc": "Center of the chemistry world box in the global frame.",
            },
        ),
        "half_size": (
            [1.0 * nm, 1.0 * nm, 1.0 * nm],
            {
                "doc": "Half-side lengths of the chemistry world box.",
            },
        ),
        "source_volume_name": (
            None,
            {
                "doc": "Name of the source volume from which the chemistry world box was derived.",
                "type": "str",
            },
        ),
        "pH": (
            None,
            {
                "doc": "Optional pH value associated with the chemistry world.",
            },
        ),
        "components": (
            [],
            {
                "doc": "List of ChemistryWorldComponent objects defining the chemistry-world composition.",
            },
        ),
        "scavenger_reactions": (
            [],
            {
                "doc": "List of ScavengerReaction objects defining scavenger processes.",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.g4_chemistry_world = None
        self.g4_scavenger_material = None

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["g4_chemistry_world"] = None
        state_dict["g4_scavenger_material"] = None
        return state_dict

    def close(self):
        self.g4_chemistry_world = None
        self.g4_scavenger_material = None
        super().close()

    def to_dictionary(self):
        return super().to_dictionary()

    def from_dictionary(self, d):
        super().from_dictionary(d)
        user_info = d.get("user_info", {})
        self.components = self._reconstruct_nested_gate_objects(
            user_info.get("components", []),
            ChemistryWorldComponent,
        )
        self.scavenger_reactions = self._reconstruct_nested_gate_objects(
            user_info.get("scavenger_reactions", []),
            ScavengerReaction,
        )
        self.g4_chemistry_world = None
        self.g4_scavenger_material = None

    def _reconstruct_nested_gate_objects(self, object_dicts, object_class):
        objects = []
        for object_dict in object_dicts:
            obj = create_gate_object_from_dict(object_dict)
            if not isinstance(obj, object_class):
                fatal(
                    f"Expected a serialized {object_class.__name__}, but reconstructed {type(obj).__name__}."
                )
            obj.simulation = self.simulation
            obj.from_dictionary(object_dict)
            objects.append(obj)
        return objects

    def set_box(self, translation, half_size):
        if translation is None or half_size is None:
            fatal(
                "ChemistryWorld.set_box() requires both 'translation' and 'half_size'."
            )
        if len(translation) != 3 or len(half_size) != 3:
            fatal(
                "ChemistryWorld.set_box() expects 3-vectors for both "
                f"'translation' and 'half_size'. Received {translation} and {half_size}."
            )
        self.translation = [float(v) for v in translation]
        self.half_size = [float(v) for v in half_size]
        self.source_volume_name = None

    def set_volume(self, volume):
        from .geometry.volumes import BoxVolume, VolumeBase

        if isinstance(volume, str):
            if self.simulation is None:
                fatal(
                    "Cannot resolve a chemistry-world source volume by name because "
                    "the ChemistryWorld is not attached to a simulation."
                )
            volume = self.simulation.volume_manager.get_volume(volume)
        elif not isinstance(volume, VolumeBase):
            fatal(
                "ChemistryWorld.set_volume() expects either a volume object or a volume name."
            )

        if not isinstance(volume, BoxVolume):
            fatal(
                f"Chemistry world creation from volume currently only supports BoxVolume. "
                f"Volume '{volume.name}' is a {type(volume).__name__}."
            )
        if volume.number_of_repetitions != 1:
            fatal(
                f"Chemistry world creation from volume currently does not support repeated volumes. "
                f"Volume '{volume.name}' has {volume.number_of_repetitions} placements."
            )
        if volume.mother != __world_name__:
            fatal(
                f"Chemistry world creation from volume currently requires a volume attached directly "
                f"to the world. Volume '{volume.name}' has mother '{volume.mother}'."
            )
        if not np.allclose(volume.rotation_list[0], np.identity(3)):
            fatal(
                f"Chemistry world creation from volume currently requires an axis-aligned box. "
                f"Volume '{volume.name}' has a non-identity rotation."
            )

        self.translation = [float(v) for v in volume.translation_list[0]]
        self.half_size = [float(v) / 2.0 for v in volume.size]
        self.source_volume_name = volume.name

    def add_component(self, molecule_name, concentration):
        if concentration is None or concentration < 0:
            fatal(
                f"Invalid chemistry-world concentration for species '{molecule_name}': {concentration}."
            )
        if molecule_name in self.components_by_name:
            fatal(
                f"Chemistry-world component '{molecule_name}' is already defined."
            )
        self.components.append(
            ChemistryWorldComponent(
                name=f"chemistry_world_component_{molecule_name}",
                simulation=self.simulation,
                species=molecule_name,
                concentration=concentration,
            )
        )

    def remove_component(self, molecule_name):
        for i, component in enumerate(self.components):
            if component.species == molecule_name:
                del self.components[i]
                return
        fatal(
            f"Cannot remove chemistry-world component '{molecule_name}' because it is not defined."
        )

    def add_scavenger_reaction(
        self,
        tracked_molecule,
        scavenger,
        products,
        rate_constant,
        reaction_type=0,
    ):
        reaction = ScavengerReaction(
            name=self._make_scavenger_reaction_name(
                tracked_molecule, scavenger, products
            ),
            simulation=self.simulation,
            tracked_molecule=tracked_molecule,
            scavenger=scavenger,
            products=list(products),
            rate_constant=rate_constant,
            reaction_type=reaction_type,
        )
        if reaction.rate_constant is None or reaction.rate_constant < 0:
            fatal(
                f"Invalid scavenger reaction rate constant for '{reaction.name}': {reaction.rate_constant}."
            )
        if reaction.key in self.scavenger_reactions_by_key:
            fatal(
                f"Scavenger reaction '{reaction.name}' is already defined in the chemistry world."
            )
        self.scavenger_reactions.append(reaction)

    def clear_scavenger_reactions(self):
        self.scavenger_reactions = []

    def clear_components(self):
        self.components = []

    @property
    def components_by_name(self):
        return {component.species: component for component in self.components}

    @property
    def scavenger_reactions_by_key(self):
        return {reaction.key: reaction for reaction in self.scavenger_reactions}

    @property
    def has_scavengers(self):
        return len(self.scavenger_reactions) > 0

    def _make_scavenger_reaction_name(self, tracked_molecule, scavenger, products):
        product_label = "_".join(products) if products else "none"
        return (
            f"scavenger_reaction_{tracked_molecule}_{scavenger}_{product_label}"
        )

    def validate_scavenger_configuration(self):
        component_names = [component.species for component in self.components]
        if len(set(component_names)) != len(component_names):
            fatal(
                f"Duplicate chemistry-world component species detected: {component_names}."
            )
        component_names = set(self.components_by_name.keys())
        for reaction in self.scavenger_reactions:
            if reaction.scavenger not in component_names:
                fatal(
                    f"Scavenger reaction '{reaction.name}' references scavenger species "
                    f"'{reaction.scavenger}', but this species is not defined as a chemistry-world component. "
                    f"Known component species are: {sorted(component_names)}."
                )
        reaction_keys = [reaction.key for reaction in self.scavenger_reactions]
        if len(set(reaction_keys)) != len(reaction_keys):
            fatal("Duplicate scavenger reactions detected in the chemistry world.")

    def create_g4_chemistry_world(self):
        if self.has_scavengers:
            self.validate_scavenger_configuration()
        g4_chemistry_world = g4.GateChemistryWorld()
        g4_chemistry_world.SetChemistryBoundary(self.translation, self.half_size)
        if self.pH is not None:
            g4_chemistry_world.SetPH(self.pH)
        g4_chemistry_world.ClearChemicalComponents()
        for component in self.components:
            g4_chemistry_world.AddChemicalComponent(
                component.species, component.concentration
            )
        g4_chemistry_world.ConstructChemistryBoundary()
        self.g4_chemistry_world = g4_chemistry_world
        self.g4_scavenger_material = None
        return g4_chemistry_world

    def create_g4_scavenger_material(self):
        if self.g4_chemistry_world is None:
            fatal(
                "Cannot create a G4DNAScavengerMaterial because the runtime chemistry world does not exist yet."
            )
        scavenger_material = g4.G4DNAScavengerMaterial(self.g4_chemistry_world)
        if self.pH is not None:
            if not float(self.pH).is_integer():
                fatal(
                    f"Geant4's stock scavenger material expects an integer pH value. Received: {self.pH}."
                )
            scavenger_material.SetpH(int(self.pH))
        return scavenger_material


class ChemicalSpecies(GateObject):
    """
    Parameter container for defining a chemical species for Geant4-DNA chemistry.
    This class only stores intrinsic properties of the molecule.
    """

    user_info_defaults = {
        "name": (
            None,
            {
                "doc": "Molecule name (must match the name used in G4MoleculeTable)",
                "type": "str",
            },
        ),
        "definition_name": (
            None,
            {
                "doc": "Underlying Geant4 molecule definition name. If None, use the same value as name.",
                "type": "str",
            },
        ),
        "molecular_mass": (
            None,
            {
                "doc": "Molecular mass of the molecule",
            },
        ),
        "charge": (
            0,
            {
                "doc": "Net electric charge in units of e",
                "type": "int",
            },
        ),
        "electronic_level": (
            0,
            {
                "doc": "Electronic level index (0 = ground state)",
            },
        ),
        "diffusion_radius": (
            0.0,
            {
                "doc": "Effective diffusion radius of the molecule",
            },
        ),
        "diffusion_coefficient": (
            None,
            {
                "doc": "Diffusion coefficient (e.g. m^2/s); None = use model default",
            },
        ),
    }

    def __eq__(self, other):
        if not isinstance(other, ChemicalSpecies):
            return NotImplemented
        return (
            self.name == other.name
            and self.definition_name == other.definition_name
            and self.molecular_mass == other.molecular_mass
            and self.charge == other.charge
            and self.electronic_level == other.electronic_level
            and self.diffusion_radius == other.diffusion_radius
            and self.diffusion_coefficient == other.diffusion_coefficient
        )


class ChemicalReaction(GateObject):
    """
    Parameter container for defining a bimolecular reaction in
    Geant4-DNA chemistry. This class only stores the intrinsic
    parameters of the reaction. Registration is done later in the
    chemistry list implementation.
    """

    user_info_defaults = {
        "reactant_a": (
            None,
            {
                "doc": "Name of the first reactant (must match a ChemicalSpecies.name)",
                "type": "str",
            },
        ),
        "reactant_b": (
            None,
            {
                "doc": "Name of the second reactant (must match a ChemicalSpecies.name)",
                "type": "str",
            },
        ),
        "rate_constant": (
            None,
            {
                "doc": (
                    "Reaction rate constant k in M^-1 s^-1 "
                    "(or compatible units; GATE will convert as needed)"
                ),
            },
        ),
        "products": (
            [],
            {
                "doc": (
                    "List of product species names. "
                    "May be empty, or contain one or several names."
                ),
                "type": "list_of_str",
            },
        ),
        "reaction_type": (
            0,
            {
                "doc": "Geant4-DNA reaction type. 0 = totally diffusion-controlled, 1 = partially diffusion-controlled.",
                "type": "int",
            },
        ),
    }

    @property
    def sorted_reactants(self):
        return tuple(sorted((self.reactant_a, self.reactant_b)))

    @property
    def reaction_products(self):
        return tuple(self.products)

    def __eq__(self, other):
        if not isinstance(other, ChemicalReaction):
            return NotImplemented
        return (
            self.sorted_reactants == other.sorted_reactants
            and self.reaction_products == other.reaction_products
            and self.rate_constant == other.rate_constant
            and self.reaction_type == other.reaction_type
        )


class ChemicalDissociation(GateObject):
    """
    Parameter container for defining a unimolecular dissociation reaction
    in Geant4-DNA chemistry.

    Represents reactions of the form:

        parent  →  product_1 + product_2 + ...

    This class only stores the intrinsic parameters of the dissociation.
    Registration into Geant4 is handled later by the ChemistryList
    implementation.
    """

    user_info_defaults = {
        "name": (
            None,
            {
                "doc": "Optional channel name. If None, a name is synthesized from the parent and products.",
            },
        ),
        "parent": (
            None,
            {
                "doc": (
                    "Name of the parent species that undergoes dissociation "
                    "(must match a ChemicalSpecies.name)"
                ),
            },
        ),
        "products": (
            [],
            {
                "doc": (
                    "List of product species names produced by the dissociation. "
                    "May contain one or several products."
                ),
                "type": "list_of_str",
            },
        ),
        "probability": (
            None,
            {
                "doc": (
                    "Branching probability (or weight) for this dissociation "
                    "channel. Required if the parent has multiple channels."
                ),
            },
        ),
        "energy": (
            None,
            {
                "doc": (
                    "Optional energy associated with this dissociation channel "
                    "(Geant4-DNA uses this only for some advanced models)."
                ),
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        # references to upper hierarchy level
        super().__init__(*args, **kwargs)

        self.chemistry_list = None

    def __eq__(self, other):
        if not isinstance(other, ChemicalDissociation):
            return NotImplemented
        return (
            self.name == other.name
            and self.parent == other.parent
            and tuple(self.products) == tuple(other.products)
            and self.probability == other.probability
            and self.energy == other.energy
        )


class ChemistryList(GateObject, G4VUserChemistryList):
    user_info_defaults = {
        "list_name": (
            None,
            {
                "doc": "Base Geant4 chemistry list to use and extend. If left unset, chemistry stays disabled unless a manager or actor explicitly requests a list.",
                "allowed_values": known_g4_chemistry_list_names + (None,),
            },
        ),
        "chemical_species": (
            [],
            {
                "doc": "Additional chemical species to append to the selected Geant4 chemistry list.",
            },
        ),
        "reactions": (
            [],
            {
                "doc": "Additional bimolecular reactions to append to the selected Geant4 chemistry list.",
            },
        ),
        "dissociations": (
            [],
            {
                "doc": "Additional dissociation channels to append to the selected Geant4 chemistry list.",
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__initcpp__()
        self._custom_species_constructed = False
        self._custom_reactions_constructed = False
        self._custom_dissociations_constructed = False

        self.g4_builtin_chemistry_list = None
        self.g4_scavenger_processes = []

    def __initcpp__(self):
        G4VUserChemistryList.__init__(self)

    def __getstate__(self):
        state_dict = super().__getstate__()
        state_dict["g4_builtin_chemistry_list"] = None
        state_dict["g4_scavenger_processes"] = []
        return state_dict

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()
        self.g4_builtin_chemistry_list = None
        self._custom_species_constructed = False
        self._custom_reactions_constructed = False
        self._custom_dissociations_constructed = False
        self.g4_scavenger_processes = []

    def to_dictionary(self):
        return super().to_dictionary()

    def _reconstruct_nested_gate_objects(self, object_dicts, object_class):
        objects = []
        for object_dict in object_dicts:
            obj = create_gate_object_from_dict(object_dict)
            if not isinstance(obj, object_class):
                fatal(
                    f"Expected a serialized {object_class.__name__}, but reconstructed {type(obj).__name__}."
                )
            obj.simulation = self.simulation
            obj.from_dictionary(object_dict)
            objects.append(obj)
        return objects

    def from_dictionary(self, d):
        super().from_dictionary(d)
        user_info = d.get("user_info", {})
        self.chemical_species = self._reconstruct_nested_gate_objects(
            user_info.get("chemical_species", []),
            ChemicalSpecies,
        )
        self.reactions = self._reconstruct_nested_gate_objects(
            user_info.get("reactions", []),
            ChemicalReaction,
        )
        self.dissociations = self._reconstruct_nested_gate_objects(
            user_info.get("dissociations", []),
            ChemicalDissociation,
        )
        for dissociation in self.dissociations:
            dissociation.chemistry_list = self
        self.g4_builtin_chemistry_list = None
        self._custom_species_constructed = False
        self._custom_reactions_constructed = False
        self._custom_dissociations_constructed = False
        self.g4_scavenger_processes = []

    def close(self):
        # The user-facing ChemistryList can be registered into the
        # G4DNAChemistryManager as the active chemistry list. Explicitly
        # deregister it before dropping Python references so Geant4 no longer
        # holds a raw pointer back to this trampoline object.
        if self.g4_builtin_chemistry_list is not None:
            g4.G4DNAChemistryManager.Instance().Deregister(self)
        self.g4_builtin_chemistry_list = None
        self._custom_species_constructed = False
        self._custom_reactions_constructed = False
        self._custom_dissociations_constructed = False
        self.g4_scavenger_processes = []
        super().close()

    @property
    def g4_molecule_table(self):
        return G4MoleculeTable.Instance()

    @property
    def chemical_species_by_name(self):
        return {species.name: species for species in self.chemical_species}

    @property
    def reactions_by_key(self):
        return {self._reaction_key(reaction): reaction for reaction in self.reactions}

    @property
    def dissociations_by_key(self):
        return {
            self._dissociation_key(dissociation): dissociation
            for dissociation in self.dissociations
        }

    def initialize_before_runmanager(self):
        if self.list_name in (None, ""):
            if self.has_customizations():
                fatal(
                    "Chemistry customizations were requested, but no base chemistry list_name was resolved. "
                    "Please configure ChemistryManager.chemistry_list_name (or an equivalent actor request) "
                    "to a known Geant4 chemistry list before adding custom species, reactions or dissociations."
                )
            return
        try:
            chemistry_list_class = getattr(g4, self.list_name)
        except AttributeError:
            fatal(f"Chemistry list '{self.list_name}' is not bound in opengate_core.")
        self._custom_species_constructed = False
        self._custom_reactions_constructed = False
        self._custom_dissociations_constructed = False
        self.g4_builtin_chemistry_list = chemistry_list_class()
        # Built-in Geant4 chemistry lists register themselves with the
        # G4DNAChemistryManager in their constructor. We only use the built-in
        # object as a provider of default chemistry callbacks, so deregister it
        # immediately and let the user-facing ChemistryList be the sole
        # registered chemistry-list identity.
        g4.G4DNAChemistryManager.Instance().Deregister(self.g4_builtin_chemistry_list)
        g4.G4DNAChemistryManager.Instance().SetChemistryList(self)

    def _make_helper_name(self, prefix, *parts):
        raw = "_".join(str(part) for part in parts if part not in (None, ""))
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")
        if safe == "":
            safe = prefix
        return f"{prefix}_{safe}"

    def _coerce_species(self, species=None, **kwargs):
        if isinstance(species, ChemicalSpecies):
            if kwargs:
                fatal(
                    "ChemistryList.add_chemical_species() received both a ChemicalSpecies object and keyword parameters."
                )
            return species
        if species is not None:
            fatal(
                f"ChemistryList.add_chemical_species expects a ChemicalSpecies or keyword parameters, got {type(species)}."
            )
        if "name" not in kwargs or kwargs["name"] in (None, ""):
            fatal(
                "ChemistryList.add_chemical_species() requires the chemical species name."
            )
        return ChemicalSpecies(**kwargs)

    def _coerce_reaction(self, reaction=None, **kwargs):
        if isinstance(reaction, ChemicalReaction):
            if kwargs:
                fatal(
                    "ChemistryList.add_reaction() received both a ChemicalReaction object and keyword parameters."
                )
            return reaction
        if reaction is not None:
            fatal(
                f"ChemistryList.add_reaction expects a ChemicalReaction or keyword parameters, got {type(reaction)}."
            )
        required = ("reactant_a", "reactant_b", "rate_constant")
        missing = [key for key in required if kwargs.get(key) in (None, "")]
        if missing:
            fatal(
                f"ChemistryList.add_reaction() is missing required parameters: {missing}."
            )
        products = kwargs.get("products", [])
        reaction_type = kwargs.get("reaction_type", 0)
        return ChemicalReaction(
            name=self._make_helper_name(
                "reaction",
                kwargs["reactant_a"],
                kwargs["reactant_b"],
                "_".join(str(product) for product in products),
                reaction_type,
            ),
            **kwargs,
        )

    def _coerce_dissociation(self, dissociation=None, **kwargs):
        if isinstance(dissociation, ChemicalDissociation):
            if kwargs:
                fatal(
                    "ChemistryList.add_chemical_dissociation() received both a ChemicalDissociation object and keyword parameters."
                )
            return dissociation
        if dissociation is not None:
            fatal(
                f"ChemistryList.add_chemical_dissociation expects a ChemicalDissociation or keyword parameters, got {type(dissociation)}."
            )
        if kwargs.get("parent") in (None, ""):
            fatal(
                "ChemistryList.add_chemical_dissociation() requires the parent species name."
            )
        if "name" not in kwargs or kwargs["name"] in (None, ""):
            kwargs["name"] = self._make_helper_name(
                "dissociation",
                kwargs["parent"],
                "_".join(str(product) for product in kwargs.get("products", [])),
            )
        return ChemicalDissociation(**kwargs)

    def add_chemical_species(self, species=None, **kwargs):
        species = self._coerce_species(species, **kwargs)
        if species.name in self.chemical_species_by_name:
            fatal(
                f"This chemistry list already has a chemical species named '{species.name}'."
            )
        self.chemical_species.append(species)

    def add_reaction(self, reaction=None, **kwargs):
        reaction = self._coerce_reaction(reaction, **kwargs)
        reaction_key = self._reaction_key(reaction)
        if reaction_key in self.reactions_by_key:
            fatal(f"This chemistry list already has a reaction '{reaction_key}'.")
        self.reactions.append(reaction)

    def add_chemical_dissociation(self, dissociation=None, **kwargs):
        dissociation = self._coerce_dissociation(dissociation, **kwargs)
        dissociation_key = self._dissociation_key(dissociation)
        if dissociation_key in self.dissociations_by_key:
            fatal(
                f"This chemistry list already has a dissociation channel '{dissociation_key}'."
            )
        dissociation.chemistry_list = self
        self.dissociations.append(dissociation)

    def _reaction_key(self, reaction):
        reactants = " + ".join(reaction.sorted_reactants)
        products = " + ".join(reaction.reaction_products)
        return f"{reactants} -> {products} " f"[type={reaction.reaction_type}]"

    def _dissociation_key(self, dissociation):
        if dissociation.name not in (None, ""):
            return dissociation.name
        return f"{dissociation.parent} -> {' + '.join(dissociation.products)}"

    def has_customizations(self):
        return any(
            (
                len(self.chemical_species) > 0,
                len(self.reactions) > 0,
                len(self.dissociations) > 0,
            )
        )

    def _construct_custom_species(self):
        if self._custom_species_constructed:
            return
        for species in self.chemical_species:
            configuration = self.g4_molecule_table.GetConfiguration(species.name)
            if configuration is not None:
                if species.diffusion_coefficient is not None:
                    configuration.SetDiffusionCoefficient(species.diffusion_coefficient)
                if species.diffusion_radius is not None:
                    configuration.SetVanDerVaalsRadius(species.diffusion_radius)
                if species.molecular_mass is not None:
                    configuration.SetMass(species.molecular_mass)
                continue
            definition_name = (
                species.definition_name
                if species.definition_name not in (None, "")
                else species.name
            )
            definition = self.g4_molecule_table.GetMoleculeDefinition(definition_name)
            if definition is None:
                diffusion_coefficient = (
                    species.diffusion_coefficient
                    if species.diffusion_coefficient is not None
                    else 0.0
                )
                definition = self.g4_molecule_table.CreateMoleculeDefinition(
                    definition_name,
                    diffusion_coefficient,
                )
            configuration = self.g4_molecule_table.CreateConfiguration(
                species.name,
                definition,
                species.charge,
                (
                    species.diffusion_coefficient
                    if species.diffusion_coefficient is not None
                    else -1.0
                ),
            )
            if species.diffusion_coefficient is not None:
                configuration.SetDiffusionCoefficient(species.diffusion_coefficient)
            if species.diffusion_radius is not None:
                configuration.SetVanDerVaalsRadius(species.diffusion_radius)
            if species.molecular_mass is not None:
                configuration.SetMass(species.molecular_mass)
        self._custom_species_constructed = True

    def _construct_custom_reactions(self):
        if self._custom_reactions_constructed:
            return
        for reaction in self.reactions:
            reactant_a_name, reactant_b_name = reaction.sorted_reactants
            reactant_a = self.g4_molecule_table.GetConfiguration(reactant_a_name)
            reactant_b = self.g4_molecule_table.GetConfiguration(reactant_b_name)
            if reactant_a is None or reactant_b is None:
                fatal(
                    f"Cannot add reaction '{self._reaction_key(reaction)}' because one or both reactants are unknown."
                )
            reaction_data = g4.G4DNAMolecularReactionData(
                reaction.rate_constant,
                reactant_a,
                reactant_b,
            )
            reaction_data.SetReactionType(reaction.reaction_type)
            for product_name in reaction.reaction_products:
                # Match Geant4's /chem/reaction/add behavior: H2O is treated as
                # the implicit solvent and is not inserted as an explicit
                # reaction-table product.
                if product_name == "H2O":
                    continue
                product = self.g4_molecule_table.GetConfiguration(product_name)
                if product is None:
                    fatal(
                        f"Cannot add reaction product '{product_name}' because its molecular configuration is unknown."
                    )
                reaction_data.AddProduct(product)
            g4.G4DNAMolecularReactionTable.GetReactionTable().SetReaction(reaction_data)
        self._custom_reactions_constructed = True

    def _construct_custom_dissociations(self):
        if self._custom_dissociations_constructed:
            return
        for dissociation in self.dissociations:
            parent_configuration = self.g4_molecule_table.GetConfiguration(
                dissociation.parent
            )
            if parent_configuration is None:
                fatal(
                    f"Cannot add dissociation for unknown parent species '{dissociation.parent}'."
                )
            parent_definition = parent_configuration.GetDefinition()
            channel = g4.G4MolecularDissociationChannel(
                self._dissociation_key(dissociation)
            )
            if dissociation.energy is not None:
                channel.SetEnergy(dissociation.energy)
            if dissociation.probability is not None:
                channel.SetProbability(dissociation.probability)
            for product_name in dissociation.products:
                product = self.g4_molecule_table.GetConfiguration(product_name)
                if product is None:
                    fatal(
                        f"Cannot add dissociation product '{product_name}' because its molecular configuration is unknown."
                    )
                channel.AddProduct(product)
            parent_definition.AddDecayChannel(dissociation.parent, channel)
        self._custom_dissociations_constructed = True

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructParticle(self):
        # Built-in Geant4 chemistry lists use ConstructParticle() as the hook
        # that populates their molecular species.
        self.ConstructMolecule()

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructProcess(self):
        self.g4_builtin_chemistry_list.ConstructProcess()
        self._construct_scavenger_processes()

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructMolecule(self):
        self.g4_builtin_chemistry_list.ConstructMolecule()
        self._construct_custom_species()

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructDissociationChannels(self):
        self.g4_builtin_chemistry_list.ConstructDissociationChannels()
        self._construct_custom_dissociations()

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructReactionTable(self, reaction_table):
        self.g4_builtin_chemistry_list.ConstructReactionTable(reaction_table)
        self._construct_custom_reactions()

    @requires_fatal("g4_builtin_chemistry_list")
    def ConstructTimeStepModel(self, reaction_table):
        self.g4_builtin_chemistry_list.ConstructTimeStepModel(reaction_table)

    def _construct_scavenger_processes(self):
        if self.simulation is None:
            return
        chemistry_world = self.simulation.chemistry_manager.chemistry_world
        if chemistry_world is None or chemistry_world.has_scavengers is False:
            return
        if chemistry_world.g4_chemistry_world is None:
            fatal(
                "Cannot construct scavenger processes because the runtime chemistry world is not available."
            )

        chemistry_world.validate_scavenger_configuration()
        # G4DNAScavengerProcess caches the scavenger material in
        # BuildPhysicsTable(), so the chemistry-world components and the
        # scheduler-owned scavenger material must already exist before Geant4
        # builds the chemistry physics tables.
        chemistry_world.g4_chemistry_world.ConstructChemistryComponents()
        if chemistry_world.g4_scavenger_material is None:
            chemistry_world.g4_scavenger_material = (
                chemistry_world.create_g4_scavenger_material()
            )
        g4.G4Scheduler.Instance().SetScavengerMaterial(
            chemistry_world.g4_scavenger_material
        )
        physics_list_helper = g4.G4PhysicsListHelper.GetPhysicsListHelper()
        scavenger_processes = {}

        for scavenger_reaction in chemistry_world.scavenger_reactions:
            tracked_conf = self.g4_molecule_table.GetConfiguration(
                scavenger_reaction.tracked_molecule, False
            )
            if tracked_conf is None:
                fatal(
                    f"Scavenger reaction '{scavenger_reaction.name}' references tracked molecule "
                    f"'{scavenger_reaction.tracked_molecule}', but this molecular configuration is unknown."
                )
            scavenger_conf = self.g4_molecule_table.GetConfiguration(
                scavenger_reaction.scavenger, False
            )
            if scavenger_conf is None:
                fatal(
                    f"Scavenger reaction '{scavenger_reaction.name}' references scavenger species "
                    f"'{scavenger_reaction.scavenger}', but this molecular configuration is unknown."
                )

            process = scavenger_processes.get(scavenger_reaction.tracked_molecule)
            if process is None:
                process = g4.G4DNAScavengerProcess(
                    f"G4DNAScavengerProcess_{scavenger_reaction.tracked_molecule}",
                    chemistry_world.g4_chemistry_world,
                )
                scavenger_processes[scavenger_reaction.tracked_molecule] = process

            reaction_data = g4.G4DNAMolecularReactionData(
                scavenger_reaction.rate_constant,
                tracked_conf,
                scavenger_conf,
            )
            reaction_data.SetReactionType(scavenger_reaction.reaction_type)
            for product_name in scavenger_reaction.products:
                product_conf = self.g4_molecule_table.GetConfiguration(
                    product_name, False
                )
                if product_conf is None:
                    fatal(
                        f"Scavenger reaction '{scavenger_reaction.name}' references product "
                        f"'{product_name}', but this molecular configuration is unknown."
                    )
                reaction_data.AddProduct(product_conf)
            process.SetReaction(tracked_conf, reaction_data)

        for tracked_molecule, process in scavenger_processes.items():
            tracked_definition = self.g4_molecule_table.GetConfiguration(
                tracked_molecule, True
            ).GetDefinition()
            physics_list_helper.RegisterProcess(process, tracked_definition)

        self.g4_scavenger_processes = list(scavenger_processes.values())


class ChemistryCustomList(GateObject, G4VUserChemistryList):

    user_info_defaults = {
        "chemical_species": (
            [],
            {
                "help": "Chemical species used by this chemistry list. ",
            },
        ),
        "reactions": (
            [],
            {
                "help": "Chemical reactions used by this chemistry list. ",
            },
        ),
        "dissociations": (
            [],
            {
                "help": "Chemical dissociations used by this chemistry list. ",
                "read_only": True,
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        # references to upper hierarchy level
        super().__init__(*args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        G4VUserChemistryList.__init__(self)

    def __getstate__(self):
        state_dict = super().__getstate__()
        return state_dict

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def close(self):
        super().close()

    @property
    def g4_molecule_table(self):
        return G4MoleculeTable.Instance()

    def add_chemical_dissociation(self, dissociation):
        if dissociation.name not in self.dissociations:
            self.dissociations[dissociation.name] = dissociation
            self.dissociations[dissociation.name].chemistry_list = self
        else:
            fatal(
                f"This chemistry list already has a dissociation called {dissociation.name}."
            )

    def find_g4_molecule(self, name):
        return self.g4_molecule_table.FindMoleculeDefinition(name)

    def initialize(self):
        pass

    # The augmented physics list uses the physics-list lifecycle names.
    # For chemistry lists, ConstructParticle maps naturally to ConstructMolecule.
    def ConstructParticle(self):
        self.ConstructMolecule()

    # Geant4-DNA chemistry setup is completed through G4DNAChemistryManager.Initialize().
    # Keep this method as a no-op so chemistry lists can participate in the
    # augmented physics list lifecycle without needing a separate close phase.
    # lifecycle without depending on Geant4's chemistry/physics double inheritance.
    def ConstructProcess(self):
        pass

    def ConstructMolecule(self):
        for species in self.chemical_species:
            self.g4_molecule_table.CreateMoleculeDefinition(
                species.name,
                species.molecular_mass,
                species.charge,
                species.electronic_level,
                species.diffusion_radius,
            )

    def ConstructReactionTable(self, reaction_table):
        for reaction_name, reaction in self.reactions.items():
            g4_reactant_a = self.find_g4_molecule(reaction.reactant_a)
            g4_reactant_b = self.find_g4_molecule(reaction.reactant_b)
            g4_products = [self.find_g4_molecule(p) for p in reaction.products]
            reaction_table.SetReaction(
                g4_reactant_a, g4_reactant_b, reaction.rate_constant, g4_products
            )

    def ConstructDissociationChannels(self):
        pass

    def ConstructTimeStepModel(self, reaction_table):
        pass


process_cls(ChemistryWorldComponent)
process_cls(ScavengerReaction)
process_cls(ChemistryWorld)
process_cls(ChemistryList)
process_cls(ChemistryCustomList)
