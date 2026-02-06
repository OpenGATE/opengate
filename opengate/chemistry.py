from .base import GateObject
from .utility import g4_units, fatal
from .decorators import requires_fatal


from opengate_core import G4MoleculeTable, G4VUserChemistryList

from box import Box


g = g4_units.g
mole = g4_units.mole
nm = g4_units.nm


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
    }


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


class ChemistryListBase(GateObject, G4VUserChemistryList):

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

    @property
    def g4_molecule_table(self):
        return G4MoleculeTable.Instance()

    def add_chemical_dissociation(self, dissociation):
        if dissociation.name not in self.dissociations:
            self.dissociations[dissociation.name] = dissociation
            self.dissociations[dissociation.name].chemistry_list = self
        else:
            fatal(f"This chemistry list already has a dissociation called {dissociation.name}.")

    def find_g4_molecule(self, name):
        return self.g4_molecule_table.FindMoleculeDefinition(name)

    def ConstructMolecule(self):
        for species in self.chemical_species:
            self.g4_molecule_table.CreateMoleculeDefinition(species.name,
                                                            species.molecular_mass,
                                                            species.charge,
                                                            species.electronic_level,
                                                            species.diffusion_radius)

    def ConstructReactionTable(self, reaction_table):
        for reaction_name, reaction in self.reactions.items():
            g4_reactant_a = self.find_g4_molecule(reaction.reactant_a)
            g4_reactant_b = self.find_g4_molecule(reaction.reactant_a)
            g4_products = [self.find_g4_molecule(p) for p in reaction.products]
            reaction_table.SetReaction(g4_reactant_a, g4_reactant_b, reaction.rate_constant, g4_products)

    def ConstructDissociationChannels(self):
        pass

    def ConstructTimeStepModel(self):
        pass


class DefaultChemistryList(ChemistryListBase):

    def __init__(self, *args, **kwargs) -> None:
        # references to upper hierarchy level
        kwargs["chemical_species"] = [ChemicalSpecies(name=k, **params) for k, params in default_chemical_species.items()]
        super().__init__(name="default_chemistry_list", *args, **kwargs)
    
    def initialize(self):
        self.g4_molecule_table = G4MoleculeTable.Instance()

