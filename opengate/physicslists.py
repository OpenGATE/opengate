import opengate_core as g4

from .exception import fatal


def retrieve_g4_physics_constructor_class(g4_physics_constructor_class_name):
    """
    Dynamically create a class with the given PhysicList
    Only possible if the class exist in g4
    """
    try:
        a = getattr(g4, g4_physics_constructor_class_name)
        assert g4_physics_constructor_class_name == a.__name__
        return a
    except AttributeError:
        fatal(
            f"Cannot find the class {g4_physics_constructor_class_name} in opengate_core"
        )


def create_modular_physics_list_class(g4_physics_constructor_class_name):
    """
    Create a class (not on object!) which:
    - inherits from g4.G4VModularPhysicsList
    - register a single G4 PhysicsConstructor (inherited from G4VPhysicsConstructor)
    - has the same name as this PhysicsConstructor
    """
    physics_constructor_class = retrieve_g4_physics_constructor_class(
        g4_physics_constructor_class_name
    )

    class ModularPhysicsList(g4.G4VModularPhysicsList):
        g4_physics_constructor_class = physics_constructor_class

        def __init__(self, verbosity):
            g4.G4VModularPhysicsList.__init__(self)
            self.g4_physics_constructor = self.g4_physics_constructor_class(verbosity)
            self.RegisterPhysics(self.g4_physics_constructor)

    ModularPhysicsList.__name__ = g4_physics_constructor_class_name
    ModularPhysicsList.__qualname__ = g4_physics_constructor_class_name
    return ModularPhysicsList


def create_physics_list_wrapper_class(physics_list_class):
    """
    Create a thin wrapper around a physics list class.

    The wrapper remains a Geant4 physics list, while optionally forwarding the
    initialization lifecycle to a chemistry list.
    """

    class PhysicsListWrapper(physics_list_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # The chemistry engine injects the chemistry list later, once it has
            # resolved and instantiated the runtime object for this simulation.
            self.chemistry_list = None

        def set_chemistry_list(self, chemistry_list):
            self.chemistry_list = chemistry_list

        def close(self):
            # Release the chemistry-list ref explicitly so the runtime ownership
            # remains with the chemistry engine and teardown order stays obvious.
            self.chemistry_list = None

        def ConstructParticle(self):
            super().ConstructParticle()
            if self.chemistry_list is not None:
                self.chemistry_list.ConstructParticle()

        def ConstructProcess(self):
            super().ConstructProcess()
            if self.chemistry_list is not None:
                self.chemistry_list.ConstructProcess()

    PhysicsListWrapper.__name__ = f"{physics_list_class.__name__}Wrapper"
    PhysicsListWrapper.__qualname__ = PhysicsListWrapper.__name__
    return PhysicsListWrapper


reference_physics_list_base_class_names = (
    "FTFP_BERT",
    "FTFP_BERT_ATL",
    "FTFP_BERT_HP",
    "FTFP_BERT_TRV",
    "FTFQGSP_BERT",
    "FTFP_INCLXX",
    "FTFP_INCLXX_HP",
    "FTF_BIC",
    "LBE",
    "NuBeam",
    "QBBC",
    "QGSP_BERT",
    "QGSP_BERT_HP",
    "QGSP_BIC",
    "QGSP_BIC_HP",
    "QGSP_BIC_AllHP",
    "QGSP_BIC_HPT",
    "QGSP_FTFP_BERT",
    "QGSP_INCLXX",
    "QGSP_INCLXX_HP",
    "QGS_BIC",
    "Shielding",
    "ShieldingLEND",
)

reference_physics_list_em_extensions = {
    "_EM0": None,
    "_EMV": "G4EmStandardPhysics_option1",
    "_EMX": "G4EmStandardPhysics_option2",
    "_EMY": "G4EmStandardPhysics_option3",
    "_EMZ": "G4EmStandardPhysics_option4",
    "_LIV": "G4EmLivermorePhysics",
    "_PEN": "G4EmPenelopePhysics",
    "_GS": "G4EmStandardPhysicsGS",
    "__GS": "G4EmStandardPhysicsGS",
    "_LE": "G4EmLowEPPhysics",
}

reference_physics_list_special_builders = {
    "Shielding_HP": {"base": "Shielding"},
    "ShieldingM": {"base": "Shielding", "ctor_args": ("HP", "M", False)},
    "ShieldingM_HP": {"base": "Shielding", "ctor_args": ("HP", "M", False)},
    "ShieldingLIQMD": {"base": "Shielding", "ctor_args": ("HP", "", True)},
    "ShieldingLIQMD_HP": {"base": "Shielding", "ctor_args": ("HP", "", True)},
    "FTFP_BERT_HPT": {"base": "FTFP_BERT_HP", "add_thermal_neutrons": True},
    "FTFP_INCLXX_HPT": {"base": "FTFP_INCLXX_HP", "add_thermal_neutrons": True},
    "QGSP_BERT_HPT": {"base": "QGSP_BERT_HP", "add_thermal_neutrons": True},
    "QGSP_BIC_AllHPT": {"base": "QGSP_BIC_AllHP", "add_thermal_neutrons": True},
    "QGSP_INCLXX_HPT": {"base": "QGSP_INCLXX_HP", "add_thermal_neutrons": True},
    "Shielding_HPT": {"base": "Shielding", "add_thermal_neutrons": True},
    "ShieldingLIQMD_HPT": {
        "base": "Shielding",
        "ctor_args": ("HP", "", True),
        "add_thermal_neutrons": True,
    },
    "ShieldingM_HPT": {
        "base": "Shielding",
        "ctor_args": ("HP", "M", False),
        "add_thermal_neutrons": True,
    },
}


def _split_reference_physics_list_name(physics_list_name):
    for suffix in sorted(
        reference_physics_list_em_extensions.keys(), key=len, reverse=True
    ):
        if suffix and physics_list_name.endswith(suffix):
            return physics_list_name[: -len(suffix)], suffix
    return physics_list_name, None


def create_reference_physics_list_class(physics_list_name):
    base_name, em_suffix = _split_reference_physics_list_name(physics_list_name)
    em_constructor_name = reference_physics_list_em_extensions.get(em_suffix)

    special_builder = reference_physics_list_special_builders.get(base_name)
    if special_builder is not None:
        bound_base_name = special_builder["base"]
    else:
        bound_base_name = base_name

    try:
        bound_base_class = getattr(g4, bound_base_name)
    except AttributeError:
        fatal(
            f"Cannot construct the reference physics list {physics_list_name}. "
            f"Missing bound base class {bound_base_name} in opengate_core."
        )

    def __init__(self, verbosity):
        if bound_base_name == "LBE":
            bound_base_class.__init__(self)
        elif special_builder is not None and "ctor_args" in special_builder:
            model, variant, use_liqmd = special_builder["ctor_args"]
            bound_base_class.__init__(self, verbosity, model, variant, use_liqmd)
        else:
            bound_base_class.__init__(self, verbosity)

        if special_builder is not None and special_builder.get("add_thermal_neutrons"):
            self.RegisterPhysics(g4.G4ThermalNeutrons(verbosity))

        if em_constructor_name is not None:
            self.ReplacePhysics(
                retrieve_g4_physics_constructor_class(em_constructor_name)(verbosity)
            )

    cls = type(physics_list_name, (bound_base_class,), {"__init__": __init__})
    cls.__qualname__ = physics_list_name
    return cls
