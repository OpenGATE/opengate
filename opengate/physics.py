from xml.etree import ElementTree as ET

from box import Box

from enum import Enum
import xml.etree.ElementTree as ET

import opengate_core as g4

from .exception import warning, fatal, GateImplementationError
from .definitions import FLOAT_MAX
from .decorators import requires_fatal
from .base import GateObject, process_cls

from .utility import g4_units, get_material_name_variants

# names for particle cuts
cut_particle_names = {
    "gamma": "gamma",
    "electron": "e-",
    "positron": "e+",
    "proton": "proton",
}


# translation from particle names used in Gate
# to particles names used in Geant4
def translate_particle_name_gate_to_geant4(name):
    """Convenience function to translate from names
    used in Gate to those in G4, if necessary.
    Concerns e.g. 'electron' -> 'e-'
    """
    try:
        return cut_particle_names[name]
    except KeyError:
        return name


track_structure_em_physics_aliases = {
    "G4EmDNAPhysics": "DNA_Opt0",
    "G4EmDNAPhysics_option2": "DNA_Opt2",
    "G4EmDNAPhysics_option4": "DNA_Opt4",
    "G4EmDNAPhysics_option6": "DNA_Opt6",
    "G4EmDNAPhysics_option7": "DNA_Opt7",
    "G4EmDNAPhysics_option8": "DNA_Opt8",
}


def _setter_hook_track_structure_em_physics(self, track_structure_em_physics):
    if track_structure_em_physics is None:
        return None
    try:
        return track_structure_em_physics_aliases[track_structure_em_physics]
    except KeyError:
        fatal(
            f"Unknown track-structure EM physics option '{track_structure_em_physics}'. "
            f"Allowed values are: {tuple(track_structure_em_physics_aliases.keys())}."
        )


class UserLimitsPhysics(g4.G4VPhysicsConstructor):
    """
    Class to be registered to physics list.

    It is essentially a refined version of StepLimiterPhysics which considers the user's
    particles choice of particles to which the step limiter should be added.

    """

    def __init__(self):
        """Objects of this class are created via the PhysicsEngine class.
        The user should not create objects manually.

        """
        g4.G4VPhysicsConstructor.__init__(self, "UserLimitsPhysics")
        self.physics_engine = None

        self.g4_step_limiter_storage = {}
        self.g4_special_user_cuts_storage = {}

    def close(self):
        self.g4_step_limiter_storage = None
        self.g4_special_user_cuts_storage = None
        self.physics_engine = None

    @requires_fatal("physics_engine")
    def ConstructParticle(self):
        """Needs to be defined because C++ base class declares this as purely virtual member."""
        pass

    @requires_fatal("physics_engine")
    def ConstructProcess(self):
        """Overrides method from G4VPhysicsConstructor
        that is called when the physics list is constructed.

        """
        ui = self.physics_engine.user_info_physics_manager

        particle_keys_to_consider = []
        # 'all' overrides individual settings
        if ui.user_limits_particles["all"] is True:
            particle_keys_to_consider = list(ui.user_limits_particles.keys())
        else:
            keys_to_exclude = ("all", "all_charged")
            particle_keys_to_consider = [
                p
                for p, v in ui.user_limits_particles.items()
                if v is True and p not in keys_to_exclude
            ]

        if len(particle_keys_to_consider) == 0:
            self.physics_engine.simulation_engine.simulation.warn_user(
                "user_limits_particles is False for all particles. No tracking cuts will be applied. Use sim.physics_manager.set_user_limits_particles()."
            )

        # translate to Geant4 particle names
        particles_to_consider = [
            translate_particle_name_gate_to_geant4(k) for k in particle_keys_to_consider
        ]

        for particle in g4.G4ParticleTable.GetParticleTable().GetParticleList():
            add_step_limiter = False
            add_user_special_cuts = False
            p_name = str(particle.GetParticleName())

            if p_name in particles_to_consider:
                add_step_limiter = True
                add_user_special_cuts = True

            # this reproduces the logic of the Geant4's G4StepLimiterPhysics class
            if (
                ui.user_limits_particles["all_charged"] is True
                and particle.GetPDGCharge() != 0
            ):
                add_step_limiter = True

            if add_step_limiter is True or add_user_special_cuts is True:
                pm = particle.GetProcessManager()
                if add_step_limiter is True:
                    # G4StepLimiter for the max_step_size cut
                    g4_step_limiter = g4.G4StepLimiter("StepLimiter")
                    pm.AddDiscreteProcess(g4_step_limiter, 1)
                    # store limiter and cuts in lists to
                    # to avoid garbage collection after exiting the methods
                    self.g4_step_limiter_storage[p_name] = g4_step_limiter
                if add_user_special_cuts is True:
                    # G4UserSpecialCuts for the other cuts
                    g4_user_special_cuts = g4.G4UserSpecialCuts("UserSpecialCut")
                    pm.AddDiscreteProcess(g4_user_special_cuts, 1)
                    self.g4_special_user_cuts_storage[p_name] = g4_user_special_cuts


def retrieve_g4_physics_constructor_class(g4_physics_constructor_class_name):
    """
    Dynamically retrieve the requested Geant4 physics-constructor class.
    """
    try:
        g4_class = getattr(g4, g4_physics_constructor_class_name)
        assert g4_physics_constructor_class_name == g4_class.__name__
        return g4_class
    except AttributeError:
        fatal(
            f"Cannot find the class {g4_physics_constructor_class_name} in opengate_core"
        )


def create_modular_physics_list_class(g4_physics_constructor_class_name):
    """
    Create a class (not an object) which:
    - inherits from g4.G4VModularPhysicsList
    - registers a single G4 PhysicsConstructor
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


def create_augmented_physics_list_class(physics_list_class):
    """
    Create an augmented physics list class.

    The augmented class remains a Geant4 physics list, while optionally
    forwarding part of the initialization lifecycle to a chemistry list.
    """

    class AugmentedPhysicsList(physics_list_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.chemistry_list = None

        def set_chemistry_list(self, chemistry_list):
            self.chemistry_list = chemistry_list

        def close(self):
            self.chemistry_list = None

        def ConstructParticle(self):
            super().ConstructParticle()
            if self.chemistry_list is not None:
                self.chemistry_list.ConstructParticle()

        def ConstructProcess(self):
            super().ConstructProcess()
            if self.chemistry_list is not None:
                self.chemistry_list.ConstructProcess()

    AugmentedPhysicsList.__name__ = f"{physics_list_class.__name__}Augmented"
    AugmentedPhysicsList.__qualname__ = AugmentedPhysicsList.__name__
    return AugmentedPhysicsList


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


class PhysicsListBuilder(GateObject):
    available_g4_physics_constructors = [
        "G4EmStandardPhysics",
        "G4EmStandardPhysics_option1",
        "G4EmStandardPhysics_option2",
        "G4EmStandardPhysics_option3",
        "G4EmStandardPhysics_option4",
        "G4EmStandardPhysicsGS",
        "G4EmLowEPPhysics",
        "G4EmLivermorePhysics",
        "G4EmLivermorePolarizedPhysics",
        "G4EmPenelopePhysics",
        "G4OpticalPhysics",
    ]

    available_g4_reference_physics_lists = [
        "FTFP_BERT",
        "FTFP_BERT_EMV",
        "FTFP_BERT_EMX",
        "FTFP_BERT_EMY",
        "FTFP_BERT_EMZ",
        "FTFP_BERT_HP",
        "FTFP_BERT_TRV",
        "FTFP_BERT_ATL",
        "FTFQGSP_BERT",
        "FTFP_INCLXX",
        "FTFP_INCLXX_HP",
        "FTFP_BERT_HPT",
        "FTFP_INCLXX_HPT",
        "FTF_BIC",
        "LBE",
        "NuBeam",
        "QBBC",
        "QGSP_BERT",
        "QGSP_BERT_EMV",
        "QGSP_BERT_EMX",
        "QGSP_BERT_EMY",
        "QGSP_BERT_EMZ",
        "QGSP_BERT_HP",
        "QGSP_BERT_HPT",
        "QGSP_BIC",
        "QGSP_BIC_HP",
        "QGSP_BIC_AllHP",
        "QGSP_BIC_HPT",
        "QGSP_BIC_AllHPT",
        "QGSP_FTFP_BERT",
        "QGSP_INCLXX",
        "QGSP_INCLXX_HP",
        "QGSP_INCLXX_HPT",
        "QGS_BIC",
        "Shielding",
        "ShieldingLEND",
        "Shielding_HP",
        "Shielding_HPT",
        "ShieldingM",
        "ShieldingM_HP",
        "ShieldingM_HPT",
        "ShieldingLIQMD",
        "ShieldingLIQMD_HP",
        "ShieldingLIQMD_HPT",
    ]

    special_physics_constructor_classes = {
        "G4DecayPhysics": g4.G4DecayPhysics,
        "G4RadioactiveDecayPhysics": g4.G4RadioactiveDecayPhysics,
        "G4OpticalPhysics": g4.G4OpticalPhysics,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_physics_list_classes = self.create_physics_list_classes()
        self.particle_with_biased_process_dictionary = {}

    @property
    def physics_manager(self):
        if self.simulation is not None:
            return self.simulation.physics_manager
        else:
            return None

    def __getstate__(self):
        raise GateImplementationError(
            f"It seems like {self.type_name} is getting pickled, "
            f"while this should never happen because the PhysicsManager should "
            f"remove it from its state dictionary. In fact, {self.type_name} "
            f"is not compatible with pickling. "
        )

    def __setstate__(self, d):
        self.__dict__ = d
        self.created_physics_list_classes = self.create_physics_list_classes()

    def create_physics_list_classes(self):
        created_physics_list_classes = {}
        for g4pc_name in self.available_g4_physics_constructors:
            physics_list_class = create_modular_physics_list_class(g4pc_name)
            created_physics_list_classes[g4pc_name] = (
                create_augmented_physics_list_class(physics_list_class)
            )
        for reference_name in self.available_g4_reference_physics_lists:
            reference_class = create_reference_physics_list_class(reference_name)
            created_physics_list_classes[reference_name] = (
                create_augmented_physics_list_class(reference_class)
            )
        return created_physics_list_classes

    @requires_fatal("simulation")
    def create_physics_list(self, physics_list_name):
        if physics_list_name in self.created_physics_list_classes:
            physics_list = self.created_physics_list_classes[physics_list_name](
                self.simulation.g4_verbose_level
            )
        else:
            s = (
                f"Cannot find the physic list: {physics_list_name}\n"
                f"{self.dump_info_physics_lists()}"
                f"Default is {self.physics_manager.user_info_defaults['physics_list_name']}\n"
                f"Help : https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html"
            )
            fatal(s)
        for (
            spc,
            switch,
        ) in self.simulation.physics_manager.special_physics_constructors.items():
            if switch is True:
                try:
                    physics_list.ReplacePhysics(
                        self.special_physics_constructor_classes[spc](
                            self.physics_manager.simulation.g4_verbose_level
                        )
                    )
                except KeyError:
                    fatal(
                        f"Special physics constructor named '{spc}' not found. Available constructors are: {self.special_physics_constructor_classes.keys()}."
                    )
        return physics_list

    def dump_info_physics_lists(self):
        g4_factory = g4.G4PhysListFactory()
        s = (
            "\n**** INFO about GATE physics lists ****\n"
            f"* Known Geant4 lists are: {g4_factory.AvailablePhysLists()}\n"
            f"* With EM options: {g4_factory.AvailablePhysListsEM()[1:]}\n"
            f"* Or the following simple physics lists with a single PhysicsConstructor: \n"
            f"* {self.available_g4_physics_constructors} \n"
            "**** ----------------------------- ****\n\n"
        )
        return s


class Region(GateObject):
    """FIXME: Documentation of the Region class."""

    available_track_structure_em_physics = (
        "G4EmDNAPhysics",
        "G4EmDNAPhysics_option2",
        "G4EmDNAPhysics_option4",
        "G4EmDNAPhysics_option6",
        "G4EmDNAPhysics_option7",
        "G4EmDNAPhysics_option8",
    )

    user_info_defaults = {}
    user_info_defaults["user_limits"] = (
        Box(
            {
                "max_step_size": None,
                "max_track_length": None,
                "min_ekine": None,
                "max_time": None,
                "min_range": None,
            }
        ),
        {
            "doc": "\tUser limits to be applied during tracking. \n"
            + "\tFIXME: Will be applied to all particles specified in the \n"
            + "\tlist under the `particles` keyword, if eligible.\n"
            + "\tUse `all` to apply tracking limits to all eligible particles.\n"
            + "\tThe following limits can be set:\n"
            + "\t* max_step_size\n"
            + "\t* max_track_length\n"
            + "\t* min_ekine\n"
            + "\t* max_time\n"
            + "\t* min_range\n",
            # expose_items=True means that the user_limits are also accessible directly
            # via Region.max_step_size, not only via Region.user_limits.max_step_size
            # that's more convenient for the user
            "expose_items": True,
        },
    )
    user_info_defaults["production_cuts"] = (
        Box(dict([(p, None) for p in cut_particle_names.keys()])),
        {
            "doc": "\tProduction cut per particle to be applied in volumes associated with this region.\n"
            + "\tShould be provided as key:value pair as: `particle_name` (string) : `cut_value` (numerical)\n"
            + "\tThe following particle names are allowed:\n"
            + "".join([f"\t* {p}\n" for p in cut_particle_names])
        },
    )
    user_info_defaults["em_switches"] = (
        Box([("deex", None), ("auger", None), ("pixe", None)]),
        {
            "doc": "Switch on/off EM parameters in this region. "
            "If None, the corresponding value from the world region is used.",
            "expose_items": True,
        },
    )
    user_info_defaults["track_structure_em_physics"] = (
        None,
        {
            "doc": "Track-structure EM physics option to activate in this region. "
            "Use the full Geant4 constructor names where they exist, for example "
            "`G4EmDNAPhysics_option2`, `G4EmDNAPhysics_option4`, "
            "`G4EmDNAPhysics_option6`, `G4EmDNAPhysics_option7`, and "
            "`G4EmDNAPhysics_option8`. "
            "GATE maps these values internally to the shorter Geant4 region-activation "
            "identifiers required by `G4EmParameters::AddDNA(...)`.",
            "allowed_values": available_track_structure_em_physics + (None,),
            "setter_hook": _setter_hook_track_structure_em_physics,
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        # references to upper hierarchy level
        super().__init__(*args, **kwargs)

        self.physics_engine = None

        # dictionaries to hold volumes to which this region is associated
        # self.volumes = {}
        self.root_logical_volumes = {}

        # g4_objects; will be created by resp. initialize_XXX() methods
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

        # flags for private use
        self._g4_region_initialized = False
        self._g4_user_limits_initialized = False
        self._g4_production_cuts_initialized = False

    @property
    def physics_manager(self):
        return self.simulation.physics_manager

    def reset(self):
        super().__init__(name=self.name, simulation=self.simulation)
        self.root_logical_volumes = {}

    # this version will work when Volume inherits from GateObject
    # def associate_volume(self, volume):
    #     volume_name = volume.name
    #     if volume_name not in self.root_logical_volumes.keys():
    #         self.root_logical_volumes[volume_name] = volume
    #     else:
    #         fatal(f'This volume {volume_name} is already associated with this region.')

    def close(self):
        self.release_g4_references()
        self.physics_engine = None

    def release_g4_references(self):
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

    def to_dictionary(self):
        d = super().to_dictionary()
        d["root_logical_volumes_names"] = list(self.root_logical_volumes.keys())
        return d

    def from_dictionary(self, d):
        self.reset()
        super().from_dictionary(d)
        for vname in d["root_logical_volumes_names"]:
            self.associate_volume(vname)

    def need_step_limiter(self):
        if self.user_info["user_limits"]["max_step_size"] is not None:
            return True
        else:
            return False

    def need_user_special_cut(self):
        if (
            self.user_info["user_limits"]["max_track_length"] is not None
            or self.user_info["user_limits"]["min_ekine"] is not None
            or self.user_info["user_limits"]["max_time"] is not None
            or self.user_info["user_limits"]["min_range"] is not None
        ):
            return True
        else:
            return False

    @requires_fatal("physics_manager")
    def associate_volume(self, volume):
        # Allow volume object to be passed and retrieve its name in that case
        try:
            volume_name = volume.name
        except AttributeError:
            volume_name = volume

        if volume_name in self.root_logical_volumes:
            fatal(f"This volume {volume_name} is already associated with this region.")
        self.root_logical_volumes[volume_name] = None
        self.physics_manager.volumes_regions_lut[volume_name] = self

    def dump_production_cuts(self):
        s = ""
        for pname, cut in self.production_cuts.items():
            if cut is not None:
                s += f"{pname}: {cut}\n"
        return s

    @requires_fatal("physics_engine")
    def initialize_before_runmanager(self):
        """Perform Python-side region setup before G4RunManager.Initialize()."""
        # Only Python objects are touched here. The actual G4Region cannot be
        # created yet because G4LogicalVolume objects appear during geometry
        # construction inside G4RunManager.Initialize().
        self.initialize_volume_dictionaries()

    @requires_fatal("physics_engine")
    def initialize_during_runmanager(self):
        """Create and attach the G4Region during geometry construction."""
        # This runs from VolumeEngine.Construct(), i.e. after logical volumes
        # exist but still early enough for Geant4 physics construction to see
        # the region-based EM configuration.
        self.initialize_g4_region()

    @requires_fatal("physics_engine")
    def initialize_after_runmanager(self):
        """Finalize region-related G4 objects after G4RunManager.Initialize()."""
        self.initialize_g4_production_cuts()
        self.initialize_g4_user_limits()
        self.initialize_g4_region()

    # This method is currently necessary because the actual volume objects
    # are only created at some point during initialization
    @requires_fatal("physics_engine")
    def initialize_volume_dictionaries(self):
        if self.physics_engine is None:
            fatal("No physics_engine defined.")
        for vname in self.root_logical_volumes.keys():
            self.root_logical_volumes[vname] = (
                self.physics_engine.simulation_engine.volume_engine.get_volume(vname)
            )

    def initialize_g4_region(self):
        if self._g4_region_initialized is not True:
            rs = g4.G4RegionStore.GetInstance()
            self.g4_region = rs.FindOrCreateRegion(self.user_info.name)

            for vol in self.root_logical_volumes.values():
                self.g4_region.AddRootLogicalVolume(vol.g4_logical_volume, True)
                vol.g4_logical_volume.SetRegion(self.g4_region)

            self._g4_region_initialized = True

        if self.g4_user_limits is not None:
            self.g4_region.SetUserLimits(self.g4_user_limits)

        if self.g4_production_cuts is not None:
            self.g4_region.SetProductionCuts(self.g4_production_cuts)

    def initialize_g4_production_cuts(self):
        self.user_info = Box(self.user_info)

        if self._g4_production_cuts_initialized is True:
            return
        if self.g4_production_cuts is None:
            self.g4_production_cuts = g4.G4ProductionCuts()

        # 'all' overrides individual cuts per particle
        try:
            cut_for_all = self.user_info["production_cuts"]["all"]
        except KeyError:
            cut_for_all = None
        if cut_for_all is not None:
            for pname in self.user_info["production_cuts"].keys():
                if pname == "all":
                    continue
                g4_pname = translate_particle_name_gate_to_geant4(pname)
                self.g4_production_cuts.SetProductionCut(cut_for_all, g4_pname)
        else:
            for pname, cut in self.user_info["production_cuts"].items():
                if pname == "all":
                    continue
                # translate to G4 names, e.g. electron -> e+
                g4_pname = translate_particle_name_gate_to_geant4(pname)
                if cut is not None:
                    self.g4_production_cuts.SetProductionCut(cut, g4_pname)
                # If no cut is specified by user for this particle,
                # set it to the value specified for the world region
                else:
                    global_cut = (
                        self.physics_engine.g4_augmented_physics_list.GetCutValue(
                            g4_pname
                        )
                    )
                    self.g4_production_cuts.SetProductionCut(global_cut, g4_pname)

        self._g4_production_cuts_initialized = True

    def initialize_g4_user_limits(self):
        if self._g4_user_limits_initialized is True:
            return

        # check if any user limits have been set
        # if not, it is not necessary to create g4 objects
        if all([(ul is None) for ul in self.user_info["user_limits"].values()]) is True:
            self._g4_user_limits_initialized = True
            return

        self.g4_user_limits = g4.G4UserLimits()

        if self.user_info["user_limits"]["max_step_size"] is None:
            self.g4_user_limits.SetMaxAllowedStep(FLOAT_MAX)
        else:
            self.g4_user_limits.SetMaxAllowedStep(
                self.user_info["user_limits"]["max_step_size"]
            )

        if self.user_info["user_limits"]["max_track_length"] is None:
            self.g4_user_limits.SetUserMaxTrackLength(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTrackLength(
                self.user_info["user_limits"]["max_track_length"]
            )

        if self.user_info["user_limits"]["max_time"] is None:
            self.g4_user_limits.SetUserMaxTime(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTime(
                self.user_info["user_limits"]["max_time"]
            )

        if self.user_info["user_limits"]["min_ekine"] is None:
            self.g4_user_limits.SetUserMinEkine(0.0)
        else:
            self.g4_user_limits.SetUserMinEkine(
                self.user_info["user_limits"]["min_ekine"]
            )

        if self.user_info["user_limits"]["min_range"] is None:
            self.g4_user_limits.SetUserMinRange(0.0)
        else:
            self.g4_user_limits.SetUserMinRange(
                self.user_info["user_limits"]["min_range"]
            )

        self._g4_user_limits_initialized = True

    def initialize_em_switches(self):
        # if all switches are None, nothing is to be set
        if any([v is not None for v in self.em_switches.values()]):
            values_to_set = {}
            for k, v in self.em_switches.items():
                if v is None:  # try to recover switch from world
                    values_to_set[k] = self.physics_manager.em_switches_world[k]
                    if values_to_set[k] is None:
                        fatal(
                            f"No value (True/False) provided for em_switch {k} in region {self.name} and no corresponding value set for the world either."
                        )
                else:
                    values_to_set[k] = v
            self.physics_engine.g4_em_parameters.SetDeexActiveRegion(
                self.name,
                values_to_set["deex"],
                values_to_set["auger"],
                values_to_set["pixe"],
            )


def get_enum_values(enum_class):
    # Filter out special Python attributes, methods, and pybind11 specific attributes
    return list(enum_class.__members__.keys())
    # return [
    #     attr
    #     for attr in dir(enum_class)
    #     if not attr.startswith("__")
    #        and not callable(getattr(enum_class, attr))
    #        and attr not in ["name", "value"]
    # ]


def load_optical_surface_properties_from_xml(surface_properties_file, surface_name):
    """
    This function extracts the information related to multiple surfaces
    from SurfaceProperties.xml
    """

    try:
        xml_tree = ET.parse(surface_properties_file)
    except FileNotFoundError:
        fatal(
            f"Could not find the surface_optical_properties_file {surface_properties_file}."
        )
    xml_root = xml_tree.getroot()

    found_surface_names = set()
    surface_properties = None
    for m in xml_root.findall("surface"):
        if m.get("name") == surface_name:
            surface_properties = {
                "base_properties": {
                    "surface_model": m.get("model"),
                    "surface_name": surface_name,
                    "surface_type": m.get("type"),
                    "surface_finish": m.get("finish"),
                    "surface_sigma_alpha": m.get("sigmaalpha"),
                },
                "constant_properties": {},
                "vector_properties": {},
            }

            # Handle propertyvector elements for UNIFIED Model
            for ptable in m.findall("propertiestable"):
                for prop_vector in ptable.findall("propertyvector"):
                    prop_vector_name = prop_vector.get("name")
                    prop_vector_value_unit = prop_vector.get("unit")
                    prop_vector_energy_unit = prop_vector.get("energyunit")

                    if prop_vector_value_unit is not None:
                        value_unit = g4_units[prop_vector_value_unit]
                    else:
                        value_unit = 1.0

                    if prop_vector_energy_unit is not None:
                        energy_unit = g4_units[prop_vector_energy_unit]
                    else:
                        energy_unit = 1.0

                    # Handle ve elements inside propertyvector
                    ve_energy_list = []
                    ve_value_list = []

                    for ve in prop_vector.findall("ve"):
                        ve_energy_list.append(float(ve.get("energy")) * energy_unit)
                        ve_value_list.append(float(ve.get("value")) * value_unit)

                    surface_properties["vector_properties"][prop_vector_name] = {
                        "prop_vector_value_unit": prop_vector_value_unit,
                        "prop_vector_energy_unit": prop_vector_energy_unit,
                        "ve_energy_list": ve_energy_list,
                        "ve_value_list": ve_value_list,
                    }

    if surface_properties is not None:
        return surface_properties
    else:
        fatal(
            f"No surface named {surface_name} not found in the XML file {surface_properties_file}"
        )


def load_optical_properties_from_xml(optical_properties_file, material_name):
    """This function parses an xml file containing optical material properties.
    Fetches property elements and property vector elements.

    Returns a dictionary with the properties or None if the material is not found in the file.
    """
    try:
        xml_tree = ET.parse(optical_properties_file)
    except FileNotFoundError:
        fatal(f"Could not find the optical_properties_file {optical_properties_file}.")
    xml_root = xml_tree.getroot()

    xml_entry_material = None
    for m in xml_root.findall("material"):
        # FIXME: some names might follow different conventions, e.g. 'Water' vs. 'G4_WATER'
        # using variants of the name is a possible solution, but this should be reviewed
        if str(m.get("name")) in get_material_name_variants(material_name):
            xml_entry_material = m
            break
    if xml_entry_material is None:
        warning(
            f"Could not find any optical material properties for material {material_name} "
            f"in file {optical_properties_file}."
        )
        return

    material_properties = {"constant_properties": {}, "vector_properties": {}}

    for ptable in xml_entry_material.findall("propertiestable"):
        # Handle property elements in XML document
        for prop in ptable.findall("property"):
            property_name = prop.get("name")
            property_value = float(prop.get("value"))
            property_unit = prop.get("unit")

            # apply unit if applicable
            if property_unit is not None:
                if len(property_unit.split("/")) == 2:
                    unit = property_unit.split("/")[1]
                else:
                    unit = property_unit
                property_value *= g4_units[unit]

            material_properties["constant_properties"][property_name] = {
                "property_value": property_value,
                "property_unit": property_unit,
            }

        # Handle propertyvector elements
        for prop_vector in ptable.findall("propertyvector"):
            prop_vector_name = prop_vector.get("name")
            prop_vector_value_unit = prop_vector.get("unit")
            prop_vector_energy_unit = prop_vector.get("energyunit")

            if prop_vector_value_unit is not None:
                value_unit = g4_units[prop_vector_value_unit]
            else:
                value_unit = 1.0

            if prop_vector_energy_unit is not None:
                energy_unit = g4_units[prop_vector.get("energyunit")]
            else:
                energy_unit = 1.0

            # Handle ve elements inside propertyvector
            ve_energy_list = []
            ve_value_list = []
            for ve in prop_vector.findall("ve"):
                ve_energy_list.append(float(ve.get("energy")) * energy_unit)
                ve_value_list.append(float(ve.get("value")) * value_unit)

            material_properties["vector_properties"][prop_vector_name] = {
                "prop_vector_value_unit": prop_vector_value_unit,
                "prop_vector_energy_unit": prop_vector_energy_unit,
                "ve_energy_list": ve_energy_list,
                "ve_value_list": ve_value_list,
            }

    return material_properties


def create_g4_optical_properties_table(material_properties_dictionary):
    """Creates and fills a G4MaterialPropertiesTable with values from a dictionary created by a parsing function,
    e.g. from an xml file.
    Returns G4MaterialPropertiesTable.
    """

    g4_material_table = g4.G4MaterialPropertiesTable()

    for property_name, data in material_properties_dictionary[
        "constant_properties"
    ].items():
        # check whether the property is already present
        create_new_key = (
            property_name not in g4_material_table.GetMaterialConstPropertyNames()
        )
        if create_new_key is True:
            warning(
                f"Found property {property_name} in optical properties file which is not known to Geant4. "
                f"I will create the property for you, but you should verify whether physics are correctly modeled."
            )
        g4_material_table.AddConstProperty(
            g4.G4String(property_name), data["property_value"], create_new_key
        )

    for property_name, data in material_properties_dictionary[
        "vector_properties"
    ].items():
        # check whether the property is already present
        create_new_key = (
            property_name not in g4_material_table.GetMaterialPropertyNames()
        )
        if create_new_key is True:
            warning(
                f"Found property {property_name} in optical properties file which is not known to Geant4. "
                f"I will create the property for you, but you should verify whether physics are correctly modeled."
            )
        g4_material_table.AddProperty(
            g4.G4String(property_name),
            data["ve_energy_list"],
            data["ve_value_list"],
            create_new_key,
            False,
        )

    return g4_material_table


class OpticalSurface(GateObject):
    """
    Class used to create an Optical Surface between two volumes

    G4OpticalSurface is used to create an optical surface

    G4LogicalBorderSurface is used to assign the optical surface
    between two volumes.
    """

    user_info_defaults = {
        "volume_from": (
            None,
            {
                "doc": "The volume from which photons propagate through the optical surface. "
            },
        ),
        "volume_to": (
            None,
            {
                "doc": "The volume into which the photons propagate coming from the surface. "
            },
        ),
        "g4_surface_name": (
            None,
            {
                "doc": "Name of the Geant4 surface to be created between volume_from and volume_to"
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.physics_engine = None

        # dictionary holding optical surface properties
        # populate from information stored in an external file
        # whose location is specified via physics_manager.surface_properties_file
        self.optical_surface_properties_dict = None

        # Store Geant4 Optical Surface object
        self.g4_optical_surface = None
        # Store Geant4 Logical Border Surface object
        self.g4_logical_border_surface = None
        # Store Geant4 object for material properties table
        self.g4_optical_surface_table = None
        # Temporary cache set by PhysicsEngine.initialize_optical_surfaces()
        # before calling initialize(). Deleted again after initialize() returns.
        self.g4_optical_surface_cache = None

    # shortcut for convenience
    @property
    def physics_manager(self):
        if self.simulation is not None:
            return self.simulation.physics_manager
        else:
            return None

    def release_g4_references(self):
        self.g4_optical_surface = None
        self.g4_logical_border_surface = None
        self.g4_optical_surface_table = None

    def close(self):
        self.release_g4_references()
        self.physics_engine = None
        super().close()

    def reset(self):
        self.__init__(name=self.name, physics_manager=self.physics_manager)

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_optical_surface"] = None
        return_dict["g4_logical_border_surface"] = None
        return_dict["g4_optical_surface_table"] = None
        return return_dict

    @requires_fatal("physics_engine")
    def initialize(self):
        """Initialize this optical border surface.

        G4OpticalSurface objects are shared across all border surfaces that use
        the same surface name: the XML is parsed once and only one G4OpticalSurface
        C++ object is created per unique surface name.  The shared cache is passed
        in via the temporary attribute self.g4_optical_surface_cache, set by
        PhysicsEngine.initialize_optical_surfaces() before calling this method.
        G4LogicalBorderSurface is always created fresh (unique per volume pair).
        """

        g4_optical_surface_cache = self.g4_optical_surface_cache

        if (
            g4_optical_surface_cache is not None
            and self.g4_surface_name in g4_optical_surface_cache
        ):
            # Cache hit: reuse the already-built G4OpticalSurface object.
            (
                self.optical_surface_properties_dict,
                self.g4_optical_surface,
                self.g4_optical_surface_table,
            ) = g4_optical_surface_cache[self.g4_surface_name]
        else:
            # Cache miss: build everything from scratch.

            self.optical_surface_properties_dict = (
                load_optical_surface_properties_from_xml(
                    self.physics_manager.surface_properties_file,
                    self.g4_surface_name,
                )
            )

            # Set properties to create G4 Optical Surface object
            surface_base_properties = self.optical_surface_properties_dict[
                "base_properties"
            ]

            # Create object of Geant4 Optical Surface
            self.g4_optical_surface = g4.G4OpticalSurface(
                g4.G4String(self.g4_surface_name)
            )

            # Set model (eg. Unified, LUT_Davis)
            model_name = surface_base_properties["surface_model"]
            try:
                model = getattr(g4.G4OpticalSurfaceModel, model_name)
                self.g4_optical_surface.SetModel(model)
            except AttributeError:
                fatal(
                    f"Unknown Model - {model_name} \n"
                    f"Available models are {get_enum_values(g4.G4OpticalSurfaceModel)}"
                )

            # Set surface type
            surface_type_name = surface_base_properties["surface_type"]
            try:
                surface_type = getattr(g4.G4SurfaceType, surface_type_name)
                self.g4_optical_surface.SetType(surface_type)
            except AttributeError:
                fatal(
                    f"Unknown Surface Type - {surface_type_name} \n"
                    f"Available Surface Types are {get_enum_values(g4.G4SurfaceType)}"
                )

            # Set finish
            surface_finish_name = surface_base_properties["surface_finish"]
            try:
                surface_finish = getattr(
                    g4.G4OpticalSurfaceFinish, surface_finish_name, None
                )
                self.g4_optical_surface.SetFinish(surface_finish)
            except AttributeError:
                fatal(
                    f"Unknown Surface Finish - {surface_finish_name} \n"
                    f"Available Surface Finishes are {get_enum_values(g4.G4OpticalSurfaceFinish)}"
                )

            # Set sigma alpha
            surface_sigma_alpha = surface_base_properties["surface_sigma_alpha"]

            if surface_sigma_alpha is not None:
                self.g4_optical_surface.SetSigmaAlpha(
                    float(surface_sigma_alpha) * g4_units.deg
                )

            # Set surface properties table
            self.g4_optical_surface_table = create_g4_optical_properties_table(
                self.optical_surface_properties_dict
            )

            self.g4_optical_surface.SetMaterialPropertiesTable(
                self.g4_optical_surface_table
            )

            # Store in cache for all subsequent border surfaces with the same name.
            if g4_optical_surface_cache is not None:
                g4_optical_surface_cache[self.g4_surface_name] = (
                    self.optical_surface_properties_dict,
                    self.g4_optical_surface,
                    self.g4_optical_surface_table,
                )

        # Clean up the temporary cache attribute.
        self.g4_optical_surface_cache = None

        # Set the Optical Surface between two volumes.
        # G4LogicalBorderSurface must always be unique per (volume_from, volume_to)
        # pair, so it is never cached.
        # g4_physical_volumes (local variables are OK because
        # permanent references are stored inside the respective python Volume instances)
        g4_physical_volume_from = (
            self.physics_engine.simulation_engine.volume_engine.get_volume(
                self.volume_from
            ).get_g4_physical_volume(0)
        )

        g4_physical_volume_to = (
            self.physics_engine.simulation_engine.volume_engine.get_volume(
                self.volume_to
            ).get_g4_physical_volume(0)
        )

        self.g4_logical_border_surface = g4.G4LogicalBorderSurface(
            g4.G4String(self.g4_surface_name),
            g4_physical_volume_from,
            g4_physical_volume_to,
            self.g4_optical_surface,
        )


process_cls(PhysicsListBuilder)
process_cls(Region)
process_cls(OpticalSurface)
