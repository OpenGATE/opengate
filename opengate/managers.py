import copy
from typing import Optional, List, Union
from box import Box
from anytree import RenderTree, LoopError
import shutil
import weakref
from pathlib import Path
import io

import opengate_core as g4
from .base import (
    GateObject,
    process_cls,
    find_all_gate_objects,
    find_paths_in_gate_object_dictionary,
)
from .definitions import __world_name__
from .engines import SimulationEngine
from .exception import fatal, warning, GateDeprecationError, GateImplementationError
from .geometry.materials import MaterialDatabase

from .utility import (
    g4_units,
    indent,
    read_mac_file_to_commands,
    ensure_directory_exists,
    insert_suffix_before_extension,
)
from .logger import *

from .physics import (
    Region,
    OpticalSurface,
    cut_particle_names,
    translate_particle_name_gate_to_geant4,
)
from .serialization import dump_json, dumps_json, loads_json, load_json
from .processing import dispatch_to_subprocess

from .sources.generic import SourceBase, GenericSource
from .sources.phspsources import PhaseSpaceSource
from .sources.voxelsources import VoxelSource
from .sources.gansources import GANSource, GANPairsSource
from .sources.beamsources import IonPencilBeamSource, TreatmentPlanPBSource
from .sources.phidsources import PhotonFromIonDecaySource
from .voxelize import voxelize_geometry

source_types = {
    "GenericSource": GenericSource,
    "PhaseSpaceSource": PhaseSpaceSource,
    "VoxelSource": VoxelSource,
    "GANSource": GANSource,
    "GANPairsSource": GANPairsSource,
    "IonPencilBeamSource": IonPencilBeamSource,
    "PhotonFromIonDecaySource": PhotonFromIonDecaySource,
    "TreatmentPlanPBSource": TreatmentPlanPBSource,
}

from .geometry.volumes import (
    VolumeBase,
    BoxVolume,
    SphereVolume,
    EllipsoidVolume,
    TrapVolume,
    ImageVolume,
    TubsVolume,
    PolyhedraVolume,
    HexagonVolume,
    TesselatedVolume,
    ConsVolume,
    TrdVolume,
    BooleanVolume,
    RepeatParametrisedVolume,
    ParallelWorldVolume,
    VolumeTreeRoot,
)
from .actors.filters import get_filter_class, FilterBase, filter_classes
from .actors.base import ActorBase

from .actors.doseactors import (
    DoseActor,
    TLEDoseActor,
    LETActor,
    FluenceActor,
    ProductionAndStoppingActor,
    RBEActor,
    REActor,
    BeamQualityActor,
    EmCalculatorActor,
)

from .actors.dynamicactors import DynamicGeometryActor
from .actors.arfactors import ARFActor, ARFTrainingDatasetActor
from .actors.miscactors import (
    SimulationStatisticsActor,
    KillActor,
    KillAccordingProcessesActor,
    AttenuationImageActor,
)
from .actors.biasingactors import (
    GenericBiasingActorBase,
    BremsstrahlungSplittingActor,
    GammaFreeFlightActor,
    ScatterSplittingFreeFlightActor,
)
from .actors.digitizers import (
    DigitizerAdderActor,
    DigitizerBlurringActor,
    DigitizerSpatialBlurringActor,
    DigitizerReadoutActor,
    DigitizerEfficiencyActor,
    DigitizerProjectionActor,
    DigitizerEnergyWindowsActor,
    DigitizerHitsCollectionActor,
    PhaseSpaceActor,
    DigiAttributeProcessDefinedStepInVolumeActor,
)

particle_names_Gate_to_G4 = {
    "gamma": "gamma",
    "electron": "e-",
    "positron": "e+",
    "proton": "proton",
    "neutron": "neutron",
}

actor_types = {
    # dose related
    "DoseActor": DoseActor,
    "TLEDoseActor": TLEDoseActor,
    "LETActor": LETActor,
    "ProductionAndStoppingActor": ProductionAndStoppingActor,
    "RBEActor": RBEActor,
    "REActor": REActor,
    "BeamQualityActor": BeamQualityActor,
    "EmCalculatorActor": EmCalculatorActor,
    "FluenceActor": FluenceActor,
    # misc
    "AttenuationImageActor": AttenuationImageActor,
    "SimulationStatisticsActor": SimulationStatisticsActor,
    "KillActor": KillActor,
    "KillAccordingProcessesActor": KillAccordingProcessesActor,
    "DynamicGeometryActor": DynamicGeometryActor,
    "ARFActor": ARFActor,
    "ARFTrainingDatasetActor": ARFTrainingDatasetActor,
    # digit
    "PhaseSpaceActor": PhaseSpaceActor,
    "DigitizerAdderActor": DigitizerAdderActor,
    "DigitizerBlurringActor": DigitizerBlurringActor,
    "DigitizerSpatialBlurringActor": DigitizerSpatialBlurringActor,
    "DigitizerReadoutActor": DigitizerReadoutActor,
    "DigitizerEfficiencyActor": DigitizerEfficiencyActor,
    "DigitizerProjectionActor": DigitizerProjectionActor,
    "DigitizerEnergyWindowsActor": DigitizerEnergyWindowsActor,
    "DigitizerHitsCollectionActor": DigitizerHitsCollectionActor,
    "DigiAttributeProcessDefinedStepInVolumeActor": DigiAttributeProcessDefinedStepInVolumeActor,
    # biasing
    "BremsstrahlungSplittingActor": BremsstrahlungSplittingActor,
    "GammaFreeFlightActor": GammaFreeFlightActor,
    "ScatterSplittingFreeFlightActor": ScatterSplittingFreeFlightActor,
}


def retrieve_g4_physics_constructor_class(g4_physics_constructor_class_name):
    """
    Dynamically create a class with the given PhysicList
    Only possible if the class exist in g4
    """
    # Retrieve the G4VPhysicsConstructor class
    try:
        a = getattr(sys.modules["opengate_core"], g4_physics_constructor_class_name)
        # sanity check:
        assert g4_physics_constructor_class_name == a.__name__
        return a
    except AttributeError:
        s = f"Cannot find the class {g4_physics_constructor_class_name} in opengate_core"
        fatal(s)


def create_modular_physics_list_class(g4_physics_constructor_class_name):
    """
    Create a class (not on object!) which:
    - inherit from g4.G4VModularPhysicsList
    - register a single G4 PhysicsConstructor (inherited from G4VPhysicsConstructor)
    - has the same name as this PhysicsConstructor
    """
    g4_physics_constructor_class = retrieve_g4_physics_constructor_class(
        g4_physics_constructor_class_name
    )
    # create the class with __init__ method
    cls = type(
        g4_physics_constructor_class_name,
        (g4.G4VModularPhysicsList,),
        {
            "g4_physics_constructor_class": g4_physics_constructor_class,
            "__init__": init_method,
        },
    )
    return cls


def init_method(self, verbosity):
    """
    Init method of the dynamically created physics list class.
    - call the init method of the super class (G4VModularPhysicsList)
    - Create and register the physics constructor (G4VPhysicsConstructor)
    """
    g4.G4VModularPhysicsList.__init__(self)
    self.g4_physics_constructor = self.g4_physics_constructor_class(verbosity)
    self.RegisterPhysics(self.g4_physics_constructor)


class FilterManager:
    """
    Manage all the Filters in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.user_info_filters = {}
        self.filters = {}

    def __str__(self):
        v = [v.name for v in self.user_info_filters.values()]
        s = f'{" ".join(v)} ({len(self.user_info_filters)})'
        return s

    @property
    def available_filters(self):
        return list(filter_classes.keys())

    def dump(self):
        n = len(self.user_info_filters)
        s = f"Number of filters: {n}"
        for Filter in self.user_info_filters.values():
            if n > 1:
                a = "\n" + "-" * 20
            else:
                a = ""
            a += f"\n {Filter}"
            s += indent(2, a)
        return s

    def get_filter(self, name):
        try:
            return self.filters[name]
        except KeyError:
            fatal(
                f"The Filter {name} is not in the current "
                f"list of Filters: {self.filters}"
            )

    def add_filter(self, filt, name=None):
        if isinstance(filt, str):
            if name is None:
                fatal("You must provide a name for the filter.")
            new_filter = self.create_filter(filt, name)
        elif isinstance(filt, FilterBase):
            new_filter = filt
        else:
            fatal(
                "You need to either provide a volume type and name, or a volume object."
            )
        if new_filter.name in self.filters:
            fatal(f"A filter with the name {new_filter.name} already exists.")
        self.filters[new_filter.name] = new_filter
        if new_filter is not filt:
            return new_filter

    def create_filter(self, filter_type, name):
        return get_filter_class(filter_type)(name=name, simulation=self.simulation)


class SourceManager(GateObject):
    """
    Manage all the sources in the simulation.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    def __init__(self, simulation, *args, **kwargs):
        kwargs["name"] = "source_manager"
        kwargs["simulation"] = simulation
        super().__init__(*args, **kwargs)
        # List of run times intervals
        self.run_timing_intervals = None
        self.current_run_interval = None
        # List of sources user info
        self.sources = {}

    def __str__(self):
        """
        str only dumps the user info on a single line
        """
        v = [v.name for v in self.sources.values()]
        s = f'{" ".join(v)} ({len(self.sources)})'
        return s

    def dump_source_types(self):
        return "\n".join(list(source_types.keys()))

    def dump_sources(self):
        n = len(self.sources)
        s = f"Number of sources: {n}"
        for source in self.sources.values():
            a = f"\n {source}"
            s += indent(2, a)
        return s

    def get_source(self, source_name):
        try:
            return self.sources[source_name]
        except KeyError:
            fatal(
                f"Cannot find the source {source_name}. "
                f"Sources included in this simulation are: {list(self.sources.keys())}"
            )
            return None  # to avoid warning

    def add_source(self, source, name):
        new_source = None
        if isinstance(source, str):
            if name is None:
                fatal("You must provide a name for the source.")
            new_source = self._create_source(source, name)
        elif isinstance(source, SourceBase):
            new_source = source
        else:
            fatal(
                "You need to either provide an actor type and name, or an actor object."
            )

        if new_source.name in self.sources:
            fatal(
                f"The source named {new_source.name} already exists. "
                f"Existing source names are: {self.sources.keys()}"
            )
        self.sources[new_source.name] = new_source
        self.sources[new_source.name].simulation = self.simulation
        # return the volume if it has not been passed as input, i.e. it was created here
        if new_source is not source:
            return new_source
        return source

    def add_source_copy(self, origin_source_name, copied_source_name):
        # get the source to copy
        orig = self.get_source(origin_source_name)
        # get its type name
        cls_name = type(orig).__name__
        # create the new source
        new_source = self.add_source(cls_name, copied_source_name)
        # copy all elements except its name
        new_source.user_info = copy.deepcopy(orig.user_info)
        new_source.user_info.name = copied_source_name
        return new_source

    def remove_source(self, source_name):
        if not source_name in self.sources:
            fatal(
                f"In 'remove_source', the source {source_name} is not in the list of sources: {self.sources}"
            )
        self.sources.pop(source_name)

    def _create_source(self, source_type, name):
        cls = None
        try:
            cls = source_types[source_type]
        except KeyError:
            fatal(
                f"Unknown source type {source_type}. "
                f"Known types are: \n."
                f"{self.dump_source_types()}."
            )
        return cls(name=name, simulation=self.simulation)

    def initialize_before_g4_engine(self):
        if len(self.sources) == 0:
            self.simulation.warn_user(
                "No configured source, no particle will be generated."
            )
        for source in self.sources.values():
            if source.initialize_source_before_g4_engine:
                source.initialize_source_before_g4_engine(source)


class ActorManager(GateObject):
    """
    Manage all the actors in the simulation
    """

    def __init__(self, simulation, *args, **kwargs) -> None:
        kwargs["name"] = "actor_manager"
        kwargs["simulation"] = simulation
        super().__init__(*args, **kwargs)
        self.user_info_actors = {}
        # dictionary of actor objects. Do not fill manually. Use add_actor() method.
        self.actors = {}

    def __str__(self):
        s = "The actor manager contains the following actors: \n"
        s += self.dump_actors()
        return s

    @property
    def sorted_actors(self):
        # consider the priority value of the actors
        # dynamic geometry actors need to come first so
        # other actors already 'see' the new geometry in their BeginOfRunAction
        dynamic_geometry_actors = [
            a for a in self.actors.values() if isinstance(a, DynamicGeometryActor)
        ]
        sorted_actors = [
            a
            for a in sorted(self.actors.values(), key=lambda a: a.priority)
            if a not in dynamic_geometry_actors
        ]
        return dynamic_geometry_actors + sorted_actors

    def reset(self):
        self.__init__(simulation=self.simulation)

    def to_dictionary(self):
        d = super().to_dictionary()
        d["actors"] = dict([(k, v.to_dictionary()) for k, v in self.actors.items()])
        return d

    def from_dictionary(self, d):
        self.reset()
        super().from_dictionary(d)
        # Create all actors
        for k, v in d["actors"].items():
            a = self.add_actor(v["object_type"], name=v["user_info"]["name"])
            a.from_dictionary(v)

    def get_actor(self, actor_name):
        try:
            return self.actors[actor_name]
        except KeyError:
            fatal(
                f"Cannot find actor {actor_name}. "
                f"Actors included in this simulation are: {list(self.actors.keys())}"
            )

    def dump_actors(self):
        n = len(self.actors)
        s = f"Number of Actors: {n}"
        for actor in self.actors.values():
            a = f"\n- {actor.name}"
            s += indent(2, a)
        return s

    def dump_actor_types(self):
        return "\n".join(list(actor_types.keys()))

    def get_actor_user_info(self, name):
        self.warn_user(
            "Deprecation warning: The function 'get_actor_user_info' will soon be removed."
            "Use my_actor.user_info instead, where 'my_actor' "
            "should be replace by your actor object. "
            "You can also access user input parameters directly, e.g. my_actor.attached_to=..."
        )
        actor = self.get_actor(name)
        return actor.user_info

    def add_actor(self, actor, name):
        new_actor = None
        if isinstance(actor, str):
            if name is None:
                fatal("You must provide a name for the actor.")
            new_actor = self._create_actor(actor, name)
        elif isinstance(actor, ActorBase):
            new_actor = actor
        else:
            fatal(
                "You need to either provide an actor type and name, or an actor object."
            )

        if new_actor.name in self.actors:
            fatal(
                f"The actor named {new_actor.name} already exists. "
                f"Existing actor names are: {self.actors.keys()}"
            )
        self.actors[new_actor.name] = new_actor
        self.actors[new_actor.name].simulation = self.simulation
        # return the volume if it has not been passed as input, i.e. it was created here
        if new_actor is not actor:
            return new_actor

    def find_actors(self, sub_str, case_sensitive=False):
        # find all actors that contain this substring
        actors = []
        if not case_sensitive:
            sub_str = sub_str.lower()
        for actor in self.actors.values():
            name = actor.name
            if not case_sensitive:
                name = name.lower()
            if sub_str in name:
                actors.append(actor)
        return actors

    def find_actors_by_type(self, type_name, sub_str=None, case_sensitive=False):
        # find all actors of a given type
        actors = []
        if not case_sensitive and sub_str is not None:
            sub_str = sub_str.lower()
        for actor in self.actors.values():
            if actor.type_name == type_name:
                if sub_str is None:
                    actors.append(actor)
                else:
                    name = actor.name
                    if not case_sensitive:
                        name = name.lower()
                    if sub_str in name:
                        actors.append(actor)
        return actors

    def find_actor_by_type(self, type_name, sub_str=None, case_sensitive=False):
        actors = self.find_actors_by_type(type_name, sub_str, case_sensitive)
        if len(actors) == 1:
            return actors[0]
        else:
            fatal(f'Found {len(actors)} actors of type "{type_name}". Expected 1.')
            return None

    def remove_actor(self, name):
        self.actors.pop(name)

    def _create_actor(self, actor_type, name):
        cls = None
        try:
            cls = actor_types[actor_type]
        except KeyError:
            fatal(
                f"Unknown actor type {actor_type}. "
                f"Known types are: \n."
                f"{self.dump_actor_types()}."
            )
        return cls(name=name, simulation=self.simulation)


class PhysicsListManager(GateObject):
    # Names of the physics constructors that can be created dynamically
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
        "G4EmDNAPhysics",
        "G4OpticalPhysics",
    ]

    special_physics_constructor_classes = {}
    special_physics_constructor_classes["G4DecayPhysics"] = g4.G4DecayPhysics
    special_physics_constructor_classes["G4RadioactiveDecayPhysics"] = (
        g4.G4RadioactiveDecayPhysics
    )
    special_physics_constructor_classes["G4OpticalPhysics"] = g4.G4OpticalPhysics
    special_physics_constructor_classes["G4EmDNAPhysics"] = g4.G4EmDNAPhysics

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # declare the attribute here as None;
        # set to dict in create_physics_list_classes()
        self.created_physics_list_classes = None
        self.create_physics_list_classes()
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
        self.create_physics_list_classes()

    def create_physics_list_classes(self):
        self.created_physics_list_classes = {}
        for g4pc_name in self.available_g4_physics_constructors:
            self.created_physics_list_classes[g4pc_name] = (
                create_modular_physics_list_class(g4pc_name)
            )

    def get_physics_list(self, physics_list_name):
        if physics_list_name in self.created_physics_list_classes:
            physics_list = self.created_physics_list_classes[physics_list_name](
                self.physics_manager.simulation.g4_verbose_level
            )
        else:
            g4_factory = g4.G4PhysListFactory()
            if g4_factory.IsReferencePhysList(physics_list_name):
                physics_list = g4_factory.GetReferencePhysList(physics_list_name)
            else:
                s = (
                    f"Cannot find the physic list: {physics_list_name}\n"
                    f"{self.dump_info_physics_lists()}"
                    f"Default is {self.physics_manager.user_info_defaults['physics_list_name']}\n"
                    f"Help : https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html"
                )
                fatal(s)
        # add special physics constructors
        for (
            spc,
            switch,
        ) in self.physics_manager.special_physics_constructors.items():
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


class PhysicsManager(GateObject):
    """
    Everything related to the physics (lists, cuts, etc.) should be here.
    """

    user_info_defaults = {
        "physics_list_name": (
            "QGSP_BERT_EMV",
            {"doc": "Name of the Geant4 physics list. "},
        ),
        "global_production_cuts": (
            Box([("all", None)] + [(pname, None) for pname in cut_particle_names]),
            {
                "doc": "Dictionary containing the production cuts (range) for gamma, electron, positron, proton. Option 'all' overrides individual cuts."
            },
        ),
        "apply_cuts": (
            True,
            {
                "doc": "Flag to turn of cuts 'on the fly'. Still under development in Gate."
            },
        ),
        "energy_range_min": (
            None,
            {
                "doc": "Minimum energy for secondary particle production. If None, physics list default is used."
            },
        ),
        "energy_range_max": (
            None,
            {
                "doc": "Maximum energy for secondary particle production. If None, physics list default is used."
            },
        ),
        "optical_properties_file": (
            Path(os.path.dirname(__file__)) / "data" / "OpticalProperties.xml",
            {
                "doc": "Path to the xml file containing the optical material properties to be used by G4OpticalPhysics. "
                "Default: file shipped with GATE.",
                "is_input_file": True,
            },
        ),
        "surface_properties_file": (
            Path(os.path.dirname(__file__)) / "data" / "SurfaceProperties.xml",
            {
                "doc": "Path to the xml file containing the surface material properties to be used by "
                "optical surface, i.e. G4LogicalBorderSurface."
                f"The default file shipped with GATE located is in "
                f"{Path(os.path.dirname(__file__)) / 'data' / 'SurfaceProperties.xml'}",
                "is_input_file": True,
            },
        ),
        "user_limits_particles": (
            Box(
                [
                    ("all", False),
                    ("all_charged", True),
                    ("gamma", False),
                    ("electron", False),
                    ("positron", False),
                    ("proton", False),
                ]
            ),
            {
                "doc": "Switch on (True) or off (False) UserLimits, e.g. step limiter, for individual particles. Default: Step limiter is applied to all charged particles (in accordance with G4 default)."
            },
        ),
        "em_parameters": (
            Box(
                [
                    ("fluo", None),
                    ("auger", None),
                    ("auger_cascade", None),
                    ("pixe", None),
                    ("deexcitation_ignore_cut", None),
                ]
            ),
            {"doc": "Switches on (True) or off (False) Geant4's EM parameters."},
        ),
        "em_switches_world": (
            Box([("deex", None), ("auger", None), ("pixe", None)]),
            {
                "doc": "Switch on/off EM parameters in the world region.",
                "expose_items": False,
            },
        ),
        "special_physics_constructors": (
            Box(
                [
                    (spc, False)
                    for spc in PhysicsListManager.special_physics_constructor_classes
                ]
            ),
            {
                "doc": "Special physics constructors to be added to the physics list, e.g. G4Decay, G4OpticalPhysics. "
            },
        ),
        "mean_energy_per_ion_pair": (
            Box(),
            {
                "doc": "Dict of material_name:energy_value, such that: sim.physics_manager.mean_energy_per_ion_pair['IEC_PLASTIC'] = 5.0 * eV. "
                "Mostly used for using acolinearity during annihilation in some materials"
            },
        ),
        "material_ionisation_potential": (
            Box(),
            {
                "doc": "Dict of material_name:energy_value, such that: sim.physics_manager.material_ionisation_potential['IEC_PLASTIC'] = 5.0 * eV. "
            },
        ),
        # "processes_to_bias": (
        #     Box(
        #         [
        #             ("all", None),
        #             ("all_charged", None),
        #             ("gamma", None),
        #             ("electron", None),
        #             ("positron", None),
        #             ("proton", None),
        #         ]
        #     ),
        #     {
        #         "doc": "Define the process to bias (if wanted) on the different particle types."
        #     },
        # ),
    }

    def __init__(self, simulation, *args, **kwargs) -> None:
        super().__init__(name="physics_manager", *args, **kwargs)

        # Keep a pointer to the current simulation
        self.simulation = simulation
        self.physics_list_manager = PhysicsListManager(
            simulation=self.simulation, name="PhysicsListManager"
        )

        # dictionary containing all the region objects
        # key=region_name, value=region_object
        self.regions = {}
        # Dictionary to quickly find the region to which a volume is associated.
        # This dictionary is updated by the region's associate_volume method.
        # Do not update manually!
        # key=volume_name, value=region=object
        # NB: It is well-defined because each volume has only one region.
        self.volumes_regions_lut = {}

        # dictionary containing all the optical surface objects
        self.optical_surfaces = {}

    def reset(self):
        self.__init__(self.simulation)

    def to_dictionary(self):
        d = super().to_dictionary()
        d["regions"] = dict([(k, v.to_dictionary()) for k, v in self.regions.items()])
        d["optical_surfaces"] = dict(
            [(k, v.to_dictionary()) for k, v in self.optical_surfaces.items()]
        )
        return d

    def from_dictionary(self, d):
        self.reset()
        super().from_dictionary(d)
        for r in d["regions"].values():
            region = self.add_region(r["user_info"]["name"])
            region.from_dictionary(r)
        for s in d["optical_surfaces"].values():
            optical_surface = self.add_optical_surface(
                s["user_info"]["volume_from"],
                s["user_info"]["volume_to"],
                s["user_info"]["g4_surface_name"],
            )
            optical_surface.from_dictionary(s)

    def __str__(self):
        s = ""
        for k, v in self.user_info.items():
            s += f"{k}: {v}\n"
        return s

    def __getstate__(self):
        # if self.simulation.verbose_getstate:
        #     self.warn_user("Getstate PhysicsManager")

        # in the case of the PhysicsManager, we make a copy of super().__getstate__()
        # rather than just using super().__getstate__() (which does not make a copy).
        # Reason: physics_list_manager would become None also in the base process
        dict_to_return = dict([(k, v) for k, v in super().__getstate__().items()])
        dict_to_return["physics_list_manager"] = None
        return dict_to_return

    def __setstate__(self, d):
        self.__dict__ = d
        self.physics_list_manager = PhysicsListManager(
            simulation=self.simulation, name="PhysicsListManager"
        )

    def _simulation_engine_closing(self):
        """This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.

        """
        # Region contain references to G4 objects, so they need to close
        for r in self.regions.values():
            r.close()

    def dump_available_physics_lists(self):
        return self.physics_list_manager.dump_info_physics_lists()

    def dump_info_physics_lists(self):
        return self.physics_list_manager.dump_info_physics_lists()

    def dump_production_cuts(self):
        s = "*** Production cuts for World: ***\n"
        for k, v in self.user_info.global_production_cuts.items():
            s += f"{k}: {v}\n"
        if len(self.regions.keys()) > 0:
            s += "*** Production cuts per regions ***\n"
            for region in self.regions.values():
                s += f"In region {region.name}:\n"
                s += region.dump_production_cuts()
        else:
            s += "*** No cuts per region defined. ***\n"
        return s

    def dump_optical_surfaces(self):
        """
        Prints each volume's name and its associated surfaces' details (surface name and connected volumes)
        from the `volume_surfaces` dictionary in a readable format.
        """
        s = "The PhysicsManager is storing the following optical surfaces:\n\n"
        for surf in self.optical_surfaces.values():
            s += str(surf)
            s += "\n"
        return s

    @property
    def enable_decay(self):
        """Properties to quickly enable decay.

        Note that setting enable_decay to False means that the physics list
        default is used, i.e. it does not forcefully remove
        G4DecayPhysics from the physics list.
        """

        switch1 = self.special_physics_constructors["G4DecayPhysics"]
        switch2 = self.special_physics_constructors["G4RadioactiveDecayPhysics"]
        if switch1 is True and switch2 is True:
            return True
        elif switch1 is False and switch2 is False:
            return False
        else:
            fatal(
                f"Inconsistent G4Decay constructors: G4DecayPhysics = {switch1}, G4RadioactiveDecayPhysics = {switch2}."
            )

    @enable_decay.setter
    def enable_decay(self, value):
        self.special_physics_constructors["G4DecayPhysics"] = value
        self.special_physics_constructors["G4RadioactiveDecayPhysics"] = value

    def add_optical_surface(self, volume_from, volume_to, g4_surface_name):
        """
        Creates an object of class OpticalSurface with surface info.

        :param volume_from: Name of the first volume (str)

        :param volume_to: Name of the second volume (str)

        :param g4_surface_name: Name of the surface between volumes (str)
        """

        name = "optical_surface_" + volume_from + "_" + volume_to

        # Throw an error if the optical surface already exists
        if name in self.optical_surfaces:
            fatal("An optical surface between these volumes already exists")

        self.optical_surfaces[name] = OpticalSurface(
            name=name,
            simulation=self.simulation,
            volume_from=volume_from,
            volume_to=volume_to,
            g4_surface_name=g4_surface_name,
        )

        return self.optical_surfaces[name]

    def add_region(self, name):
        if name in self.regions:
            fatal("A region with this name already exists.")
        self.regions[name] = Region(name=name, simulation=self.simulation)
        return self.regions[name]

    def find_or_create_region(self, volume_name):
        if volume_name not in self.volumes_regions_lut:
            region = self.add_region(volume_name + "_region")
            region.associate_volume(volume_name)
        else:
            region = self.volumes_regions_lut[volume_name]
        return region

    def get_biasing_particles_and_processes(self):
        """Build a dictionary {particles:list[processes]} by collecting information
        from all biasing actors present in the simulation.
        """

        charged_particles = {"e-", "e+", "proton"}
        all_particles = charged_particles.union({"gamma"})

        # create a dictionary with sets as entries (to ensure uniqueness)
        particles_processes = dict([(p, set()) for p in all_particles])

        for actor in self.simulation.actor_manager.actors.values():
            if isinstance(actor, GenericBiasingActorBase):
                particles = set()
                if "all" in actor.particles:
                    particles.update(all_particles)
                elif "all_charged" in actor.particles:
                    particles.update(charged_particles)
                else:
                    for particle in actor.particles:
                        p_ = translate_particle_name_gate_to_geant4(particle)
                        if p_ in all_particles:
                            particles.add(p_)
                        else:
                            fatal(
                                f"Biasing actor {actor.name} wants to apply a bias to particle '{p_}'. "
                                f"This is not possible. Compatible particles are: {list(all_particles)}. "
                            )
                for p in particles:
                    particles_processes[p].update(actor.processes)

        # convert the dictionary entries back from set to list
        return dict(
            [
                (particle, list(processes))
                for particle, processes in particles_processes.items()
            ]
        )

    # New name, more specific
    def set_production_cut(self, volume_name, particle_name, value):
        if volume_name == self.simulation.world.name:
            self.global_production_cuts[particle_name] = value
        else:
            region = self.find_or_create_region(volume_name)
            region.production_cuts[particle_name] = value

    # set methods for the user_info parameters
    # logic: every volume with user_infos must be associated
    # with a region. If it does not yet have one, created it.
    # Outlook: These setter methods might be linked to properties
    # implemented in a future version of the Volume class
    def set_max_step_size(self, volume_name, max_step_size):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_step_size"] = max_step_size

    def set_max_track_length(self, volume_name, max_track_length):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_track_length"] = max_track_length

    def set_min_ekine(self, volume_name, min_ekine):
        region = self.find_or_create_region(volume_name)
        region.user_limits["min_ekine"] = min_ekine

    def set_max_time(self, volume_name, max_time):
        region = self.find_or_create_region(volume_name)
        region.user_limits["max_time"] = max_time

    def set_min_range(self, volume_name, min_range):
        region = self.find_or_create_region(volume_name)
        region.user_limits["min_range"] = min_range

    def set_user_limits_particles(self, particle_names):
        if not isinstance(particle_names, (list, set, tuple)):
            particle_names = list([particle_names])
        for pn in list(particle_names):
            # try to get current value to check if particle_name is eligible
            try:
                _ = self.user_info.user_limits_particles[pn]
            except KeyError:
                fatal(
                    f"Found unknown particle name '{pn}' in set_user_limits_particles(). Eligible names are "
                    + ", ".join(list(self.user_info.user_limits_particles.keys()))
                    + "."
                )
            self.user_info.user_limits_particles[pn] = True


class PostProcessingManager(GateObject):
    """Everything related to post-processing. EXPERIMENTAL!"""

    user_info_defaults = {
        "auto_process": (
            True,
            {
                "doc": "Should the post-processing automatically be started at the end of the simulation?"
            },
        ),
    }

    def __init__(self, simulation, *args, **kwargs):
        super().__init__(
            *args, name="post_processing_manager", simulation=simulation, **kwargs
        )

        self.finalizers = {}
        self.post_processors = {}

    def add_post_processor(self, post_processor):
        try:
            name = post_processor.name
        except AttributeError:
            fatal("Cannot retrieve the name of the post-processor.")
        if name not in self.post_processors:
            self.post_processors[name] = post_processor
            # add finalizers to make sure the post-processor is shut down gracefully
            # when the managers is garbage collected
            self.finalizers[name] = weakref.finalize(
                post_processor, post_processor.close
            )
        else:
            fatal("A post-processor with this name has already been added. ")


class VolumeManager(GateObject):
    """
    Store and manage a hierarchical list of geometrical volumes and associated materials.
    This tree will be converted into Geant4 Solid/PhysicalVolume/LogicalVolumes
    """

    volume_types = {
        "BoxVolume": BoxVolume,
        "SphereVolume": SphereVolume,
        "EllipsoidVolume": EllipsoidVolume,
        "TrapVolume": TrapVolume,
        "ImageVolume": ImageVolume,
        "TubsVolume": TubsVolume,
        "PolyhedraVolume": PolyhedraVolume,
        "HexagonVolume": HexagonVolume,
        "ConsVolume": ConsVolume,
        "TrdVolume": TrdVolume,
        "BooleanVolume": BooleanVolume,
        "RepeatParametrisedVolume": RepeatParametrisedVolume,
        "TesselatedVolume": TesselatedVolume,
    }

    def __init__(self, simulation, *args, **kwargs) -> None:
        """
        Class that store geometry description.
        """
        # force name to VolumeManager
        kwargs["name"] = "VolumeManager"
        kwargs["simulation"] = simulation
        super().__init__(*args, **kwargs)

        self.volume_tree_root = VolumeTreeRoot(
            volume_manager=self
        )  # abstract element used as common root for volume tree
        m = g4_units.m

        # default world volume
        self.volumes = {}
        self.volumes[__world_name__] = BoxVolume(
            simulation=self.simulation,
            name=__world_name__,
            size=[3 * m, 3 * m, 3 * m],
            material="G4_AIR",
            mother=None,
        )
        # attach the world to the tree root
        self.volumes[__world_name__].parent = self.volume_tree_root

        self.parallel_world_volumes = {}

        self._need_tree_update = True  # flag to store state of volume tree

        # database of materials
        self.material_database = MaterialDatabase()

        # List of ImageBox solids
        # They need to be init after the creation of OpenGL
        # Store them to init them later
        self.solid_with_texture_init = []

    def reset(self):
        self.__init__(self.simulation)

    def __str__(self):
        s = "**** Volume manager ****\n"
        if len(self.parallel_world_volumes) > 0:
            s += f"Number of parallel worlds: {len(self.parallel_world_volumes)}\n"
            s += f"Names of the parallel worlds: {self.parallel_world_names}\n"
        s += f"Number of volumes: {len(self.volumes)}\n"
        s += "The volumes are organized in the following hierarchy:\n"
        s += self.dump_volume_tree()
        return s

    def to_dictionary(self):
        d = super().to_dictionary()
        d["volumes"] = dict([(k, v.to_dictionary()) for k, v in self.volumes.items()])
        d["parallel_world_volumes"] = list(self.parallel_world_volumes.keys())
        return d

    def from_dictionary(self, d):
        self.reset()
        super().from_dictionary(d)
        # First create all volumes
        for k, v in d["volumes"].items():
            # the world volume is always created in __init__
            if v["user_info"]["name"] != self.world_volume.name:
                self.add_volume(v["object_type"], name=v["user_info"]["name"])
        # ... then process them to make sure that any reference
        #  to a volume in the volumes dictionary is satisfied
        for k, v in d["volumes"].items():
            self.volumes[k].from_dictionary(v)

    @property
    def world_volume(self):
        return self.volumes[__world_name__]

    @property
    def all_world_volumes(self):
        """List of all world volumes, including the mass world volume."""
        world_volumes = [self.world_volume]
        world_volumes.extend(list(self.parallel_world_volumes.values()))
        return world_volumes

    @property
    def volume_names(self):
        return list(self.volumes.keys())

    @property
    def parallel_world_names(self):
        return list(self.parallel_world_volumes.keys())

    @property
    def all_volume_names(self):
        return self.volume_names + self.parallel_world_names

    @property
    def dynamic_volumes(self):
        return [vol for vol in self.volumes.values() if vol.is_dynamic]

    def get_volume(self, volume_name):
        try:
            return self.volumes[volume_name]
        except KeyError:
            try:
                return self.parallel_world_volumes[volume_name]
            except KeyError:
                fatal(
                    f"Cannot find volume {volume_name}. "
                    f"Volumes included in this simulation are: {self.volumes.keys()}"
                )

    def find_volumes(self, sub_str, case_sensitive=False):
        # find all volumes that contains this substring
        volumes = []
        if not case_sensitive:
            sub_str = sub_str.lower()
        for actor in self.volumes.values():
            name = actor.name
            if not case_sensitive:
                name = name.lower()
            if sub_str in name:
                volumes.append(actor)
        return volumes

    def update_volume_tree_if_needed(self):
        if self._need_tree_update is True:
            self.update_volume_tree()

    def update_volume_tree(self):
        for v in self.volumes.values():
            if (
                v not in self.parallel_world_volumes.values()
                and v is not self.world_volume
            ):
                try:
                    v._update_node()
                except LoopError:
                    fatal(
                        f"There seems to be a loop in the volume tree involving volume {v.name}."
                    )
        self._need_tree_update = False

    def add_volume(self, volume, name=None):
        if isinstance(volume, str):
            if name is None:
                fatal("You must provide a name for the volume.")
            new_volume = self.create_volume(volume, name)
        elif isinstance(volume, VolumeBase):
            new_volume = volume
        else:
            fatal(
                "You need to either provide a volume type and name, or a volume object."
            )

        if new_volume.name in self.all_volume_names:
            fatal(
                f"The volume name {new_volume.name} already exists. Existing volume names are: {self.volumes.keys()}"
            )
        self.volumes[new_volume.name] = new_volume
        self.volumes[new_volume.name].simulation = self.simulation
        self._need_tree_update = True
        # return the volume if it has not been passed as input, i.e. it was created here
        if new_volume is not volume:
            return new_volume

    def remove_volume(self, volume_name):
        self.volumes.pop(volume_name)

    def create_volume(self, volume_type, name):
        # check that another element with the same name does not already exist
        volume_type_variants = [volume_type, volume_type + "Volume"]
        for vt in volume_type_variants:
            if vt in self.volume_types:
                return self.volume_types[vt](name=name)
        fatal(
            f"Unknown volume type {volume_type}. Known types are: {list(self.volume_types.keys())}."
        )

    def add_parallel_world(self, name):
        if name in self.all_volume_names:
            fatal(
                f"Cannot create the parallel world named {name} because it already exists."
            )
        # constructor needs self, i.e. the volume manager
        self.parallel_world_volumes[name] = ParallelWorldVolume(name, self)
        self._need_tree_update = True

    def _simulation_engine_closing(self):
        """
        This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.
        """
        self.material_database = None

    def add_material_database(self, filename):
        if filename in self.material_database.filenames:
            fatal(f'Database "{filename}" already exist.')
        self.material_database.read_from_file(filename)

    def find_or_build_material(self, material):
        return self.material_database.FindOrBuildMaterial(material)

    def dump_volumes(self):
        s = f"Number of volumes: {len(self.volumes)}"
        for vol in self.volumes.values():
            s += indent(2, f"\n{vol}")
        return s

    def print_volumes(self):
        print(self.dump_volumes())

    def dump_volume_tree(self):
        self.update_volume_tree_if_needed()
        s = ""
        for pre, _, node in RenderTree(self.volume_tree_root):
            # FIXME: pre should be used directly but cannot be encoded correctly in Windows
            s += len(pre) * " " + f"{node.name}\n"
        return s

    def get_volume_tree(self):
        return self.volume_tree_root

    def print_volume_tree(self):
        print(self.dump_volume_tree())

    def dump_volume_types(self):
        s = ""
        for vt in self.volume_types:
            s += f"{vt} "
        return s

    def print_volume_types(self):
        print(self.dump_volume_types())

    def dump_material_database_names(self):
        return list(self.material_database.filenames)

    def print_material_database_names(self):
        print(self.dump_material_database_names())


def setter_hook_verbose_level(sim, verbose_level):
    # print(f"setter_hook_verbose_level to ", sim.log_handler_id, verbose_level)
    if sim.log_handler_id == -1:
        # Remove the default logger configuration
        logger.remove()
    else:
        # Remove the current logger configuration
        try:
            logger.remove(sim.log_handler_id)
        except:
            pass

    sim.log_handler_id = logger.add(
        sys.stdout,
        colorize=True,
        level=verbose_level,
        format=("{level.icon}<level>{message}</level>"),  # Message formatting
    )
    return verbose_level


class Simulation(GateObject):
    """
    Main class that store a simulation.
    It contains:
    - a set of global user parameters (SimulationUserInfo)
    - user parameters for Volume, Source, Actors and Filters, Physics
    - a list of g4 commands that will be set to G4 engine after the initialisation

    There is NO Geant4 engine here, it is only a set of parameters and options.
    """

    # hints for IDE
    verbose_level: int
    log_sink: str
    verbose_close: bool
    verbose_getstate: bool
    running_verbose_level: int
    g4_verbose_level: int
    g4_verbose: bool
    g4_verbose_level_tracking: int
    visu: bool
    visu_type: str
    visu_filename: Optional[Path]
    visu_verbose: bool
    visu_commands: List[str]
    visu_commands_vrml: List[str]
    visu_commands_gdml: List[str]
    check_volumes_overlap: bool
    number_of_threads: int
    force_multithread_mode: bool
    random_engine: str
    random_seed: Union[str, int]
    run_timing_intervals: List[List[float]]
    output_dir: Path
    store_json_archive: bool
    json_archive_filename: str
    store_input_files: bool
    g4_commands_before_init: List[str]
    g4_commands_after_init: List[str]
    init_only: bool
    progress_bar: bool
    dyn_geom_open_close: bool
    dyn_geom_optimise: bool

    user_info_defaults = {
        "verbose_level": (
            "INFO",
            {
                "doc": "Gate pre-run verbosity. "
                "Will display more or fewer messages during initialization. ",
                "setter_hook": setter_hook_verbose_level,
                "allowed_values": [
                    "NONE",
                    "DEBUG",
                    "INFO",
                    "WARNING",
                    "CRITICAL",
                    NONE,
                    DEBUG,
                    INFO,
                    WARNING,
                    CRITICAL,
                ],
            },
        ),
        "log_sink": (
            None,
            {
                "doc": "Log sink. "
                "If None, the default logger sys.stdout will be used. "
                "If 'str', the logger output will be available after the simulation in sim.log_output"
            },
        ),
        "verbose_close": (
            False,
            {"doc": "Switch on/off verbose output in close() methods."},
        ),
        "verbose_getstate": (
            False,
            {"doc": "Switch on/off verbose output in __getstate__() methods."},
        ),
        "running_verbose_level": (
            0,
            {
                "doc": "Gate verbosity while the simulation is running.",
                "allowed_values": (0, RUN, EVENT),
            },
        ),
        "g4_verbose_level": (
            1,
            # For an unknown reason, when verbose_level == 0, there are some
            # additional print after the G4RunManager destructor. So we default at 1
            {
                "doc": "Geant4 verbosity. With level 0, Geant4 is mostly silent. "
                "Level 1 already gives quite a bit of verbose output. "
                "Level 2 is very detailed and might affect performance. "
            },
        ),
        "g4_verbose": (False, {"doc": "Switch on/off Geant4's verbose output."}),
        "g4_verbose_level_tracking": (
            -1,
            {
                "doc": "Activate verbose tracking in Geant4 "
                "via G4 command '/tracking/verbose g4_verbose_level_tracking'."
            },
        ),
        "visu": (
            False,
            {
                "doc": "Activate visualization? "
                "Note: Use low number of primaries if you activate visualization. "
            },
        ),
        "visu_type": (
            "vrml",
            {
                "doc": "The type of visualization to be used. "
                "'qt' will start a Geant4 Qt interface. "
                "The Geant4 visualisation commands can be adapted via the parameter visu_commands.",
                "allowed_values": (
                    "qt",
                    "vrml",
                    "gdml",
                    "vrml_file_only",
                    "gdml_file_only",
                ),
            },
        ),
        "visu_filename": (
            None,
            {
                "doc": "Name of the file where visualization output is stored. Only applicable for vrml and gdml.",
                "required_type": Path,
            },
        ),
        "visu_verbose": (
            False,
            {
                "doc": "Should verbose output be generated regarding the visualization?",
            },
        ),
        "visu_commands": (
            read_mac_file_to_commands("default_visu_commands_qt.mac"),
            {
                "doc": "Geant4 commands needed to handle the visualization. "
                "By default, the Geant4 visualisation commands are the ones "
                "provided in the file ``opengate/mac/default_visu_commands_qt.mac``. "
                "Custom commands can be loaded via a .mac file, e.g.  "
                "``sim.visu_commands = gate.read_mac_file_to_commands('my_visu_commands.mac')``.",
            },
        ),
        "visu_commands_vrml": (
            read_mac_file_to_commands("default_visu_commands_vrml.mac"),
            {
                "doc": "Geant4 commands needed to handle the VRML visualization. "
                "Only used for vrml-like visualization types. ",
            },
        ),
        "visu_commands_gdml": (
            read_mac_file_to_commands("default_visu_commands_gdml.mac"),
            {
                "doc": "Geant4 commands needed to handle the GDML visualization. "
                "Only used for vrml-like visualization types. ",
            },
        ),
        "check_volumes_overlap": (
            True,
            {
                "doc": "If true, Gate will also check whether volumes overlap. "
                "Note: Geant4 checks overlaps in any case."
            },
        ),
        "number_of_threads": (
            1,
            {
                "doc": "Number of threads on which the simulation will run. "
                "Geant4's run manager will run in MT mode if more than 1 thread is requested."
                "Requires Geant4 do be compiled with Multithread flag TRUE."
            },
        ),
        "force_multithread_mode": (
            False,
            {
                "doc": "Force Geant4 to run multihthreaded even if 'number_of_threads' = 1."
            },
        ),
        "random_engine": (
            "MixMaxRng",
            {
                "doc": "Name of the Geant4 random engine to be used. "
                "MixMaxRng is recommended for multithreaded applications."
            },
        ),
        "random_seed": (
            "auto",
            {
                "doc": "Random seed to be used by the random engine. "
                "Setting a specific value will make subsequent simulation runs to produce identical results."
            },
        ),
        "run_timing_intervals": (
            [[0 * g4_units.second, 1 * g4_units.second]],
            {
                "doc": "A list of timing intervals provided as 2-element lists of begin and end values"
            },
        ),
        "output_dir": (
            ".",
            {
                "doc": "Directory to which any output is written, "
                "unless an absolute path is provided for a specific output."
            },
        ),
        "store_json_archive": (
            False,
            {
                "doc": "Automatically store a json file containing all parameters of the simulation after the run? "
                "Default: False"
            },
        ),
        "json_archive_filename": (
            Path("simulation.json"),
            {
                "doc": "Name of the json file containing all parameters of the simulation. "
                "It will be saved in the location specified via the parameter 'output_dir'. "
                "Default filename: simulation.json"
            },
        ),
        "store_input_files": (
            False,
            {"doc": "Store all input files used in the simulation? Default: False"},
        ),
        "g4_commands_before_init": (
            [],
            {
                "doc": "Geant4 commands which will be called before the G4 runmanager has initialized the simulation.",
                "required_type": str,
            },
        ),
        "g4_commands_after_init": (
            [],
            {
                "doc": "Geant4 commands which will be called after the G4 runmanager has initialized the simulation.",
                "required_type": str,
            },
        ),
        "init_only": (
            False,
            {
                "doc": "Start G4 engine initialisation but do not start the simulation.",
            },
        ),
        "progress_bar": (
            False,
            {
                "doc": "Display a progress bar during the simulation",
            },
        ),
        "dyn_geom_open_close": (
            True,
            {
                "doc": "Warning, should be True. Only set it to false if you know what your are doing"
            },
        ),
        "dyn_geom_optimise": (
            True,
            {"doc": "'Optimise' geometry when open/close during dynamic simulation. "},
        ),
    }

    def __init__(self, name="simulation", **kwargs):
        """
        The main members are:
        - managers of volumes, physics, sources, actors and filters
        - the Geant4 objects will be only built during initialisation in SimulationEngine
        """
        # init logger
        self.log_handler_id = -1
        self.log_output = ""
        setter_hook_verbose_level(self, INFO)

        # The Simulation instance should not hold a reference to itself (cycle)
        kwargs.pop("simulation", None)
        super().__init__(name=name, **kwargs)

        # list to store warning messages issued somewhere in the simulation
        self._user_warnings = []

        # main managers
        self.volume_manager = VolumeManager(self)
        self.source_manager = SourceManager(self)
        self.actor_manager = ActorManager(self)
        self.physics_manager = PhysicsManager(self)
        self.filter_manager = FilterManager(self)

        # hook functions
        self.user_hook_after_init = None
        self.user_hook_after_init_arg = None
        self.user_hook_after_run = None
        self.user_hook_log = None

        # read-only info
        self._current_random_seed = None

        self.expected_number_of_events = None

    def __str__(self):
        s = (
            f"Simulation name: {self.name} \n"
            f"Geometry       : {self.volume_manager}\n"
            f"Physics        : {self.physics_manager}\n"
            f"Sources        : {self.source_manager}\n"
            f"Actors         : {self.actor_manager}"
        )
        return s

    @property
    def output(self):
        raise GateDeprecationError(
            "You can no longer (and do not need any longer) "
            "access the simulation output via sim.output.\n"
            "Use the original actor object directly."
        )

    @property
    def use_multithread(self):
        return self.number_of_threads > 1 or self.force_multithread_mode

    @property
    def world(self):
        return self.volume_manager.world_volume

    @property
    def current_random_seed(self):
        return self._current_random_seed

    @property
    def warnings(self):
        return self._user_warnings

    def reset_warnings(self):
        self._user_warnings = []

    def warn_user(self, message):
        # We need this specific implementation because the Simulation does not hold a reference 'simulation',
        # as required by the base class implementation of warn_user()
        self._user_warnings.append(message)
        super().warn_user(message)

    def to_dictionary(self):
        d = super().to_dictionary()
        d["volume_manager"] = self.volume_manager.to_dictionary()
        d["physics_manager"] = self.physics_manager.to_dictionary()
        d["actor_manager"] = self.actor_manager.to_dictionary()
        return d

    def from_dictionary(self, d):
        super().from_dictionary(d)
        self.volume_manager.from_dictionary(d["volume_manager"])
        self.physics_manager.from_dictionary(d["physics_manager"])
        self.actor_manager.from_dictionary(d["actor_manager"])

    def to_json_string(self):
        warning("Only parts of the simulation can currently be dumped as JSON")
        return dumps_json(self.to_dictionary())

    def to_json_file(self, directory=None, filename=None):
        warning("Only parts of the simulation can currently be dumped as JSON.")
        d = self.to_dictionary()
        if filename is None:
            filename = self.json_archive_filename
        directory = self.get_output_path(directory, is_file_or_directory="d")
        with open(directory / filename, "w") as f:
            dump_json(d, f)
        # look for input files in the simulation and copy them if requested
        if self.store_input_files is True:
            self.copy_input_files(directory, dct=d)

    def from_json_string(self, json_string):
        warning("Only parts of the simulation can currently be reloaded from JSON.")
        self.from_dictionary(loads_json(json_string))

    def from_json_file(self, path):
        warning("Only parts of the simulation can currently be reloaded from JSON.")
        with open(path, "r") as f:
            self.from_dictionary(load_json(f))

    def copy_input_files(self, directory=None, dct=None):
        directory = self.get_output_path(directory, is_file_or_directory="d")
        if dct is None:
            dct = self.to_dictionary()
        input_files = []
        for go_dict in find_all_gate_objects(dct):
            input_files.extend(
                [
                    p
                    for p in find_paths_in_gate_object_dictionary(
                        go_dict, only_input_files=True
                    )
                    if p.is_file() is True
                ]
            )
        # post process the list
        raw_files = []
        for f in input_files:
            # check for image header files (mhd) and add the corresponding raw files to the list
            if f.suffix == ".mhd":
                raw_files.append(f.parent.absolute() / Path(f.stem + ".raw"))
        input_files.extend(raw_files)
        for f in input_files:
            shutil.copy2(f, directory)

    def get_output_path(self, path=None, is_file_or_directory="file", suffix=None):
        if path is None:
            # no input -> return global output directory
            p_out = Path(self.output_dir)
        else:
            # make sure type is Path
            p = Path(path)
            if not p.is_absolute():
                # prepend the global output dir if p is relative
                p_out = self.output_dir / p
            else:
                # or just keep it
                p_out = p

        if suffix is not None:
            p_out = insert_suffix_before_extension(p_out, suffix)

        # Make sure the directory exists
        if is_file_or_directory in ["file", "File", "f"]:
            n = len(p_out.parts) - 1  # last item is the filename
        elif is_file_or_directory in ["dir", "Dir", "directory", "d"]:
            n = len(p_out.parts)  # all items are part of the directory
        if len(p_out.parts) > 0 and n > 0:
            directory = Path(p_out.parts[0])
            for i in range(n - 1):
                directory /= p_out.parts[i + 1]
            ensure_directory_exists(directory)

        return p_out.absolute().resolve()

    def add_g4_command_after_init(self, command):
        raise GateDeprecationError("Use sim.g4_commands_after_init.append(COMMAND)")

    def add_g4_command_before_init(self, command):
        raise GateDeprecationError("Use sim.g4_commands_before_init.append(COMMAND)")

    # FIXME: will we become obsolete when refactoring the sources
    def get_source_user_info(self, name):
        return self.source_manager.get_source(name)

    def get_actor_user_info(self, name):
        s = self.actor_manager.get_actor_user_info(name)
        return s

    def add_volume(self, volume, name=None):
        return self.volume_manager.add_volume(volume, name)

    # call this add optical surface, from_volume, to_volume,
    def add_surface(self, volume_1, volume_2, surface_name):
        return self.physics_manager.add_surface(volume_1, volume_2, surface_name)

    def add_parallel_world(self, name):
        self.volume_manager.add_parallel_world(name)

    def add_source(self, source_type, name):
        return self.source_manager.add_source(source_type, name)

    def add_actor(self, actor_type, name):
        return self.actor_manager.add_actor(actor_type, name)

    def get_actor(self, name):
        return self.actor_manager.get_actor(name)

    def find_actors(self, sub_str, case_sensitive=False):
        return self.actor_manager.find_actors(sub_str, case_sensitive)

    def add_filter(self, filter_type, name):
        return self.filter_manager.add_filter(filter_type, name)

    @property
    def multithreaded(self):
        return self.number_of_threads > 1 or self.force_multithread_mode

    def initialize_logger(self):
        original_stdout = sys.stdout
        self.log_output = io.StringIO()
        if self.log_sink == "str":
            sys.stdout = self.log_output
        # reinstall the logger (for subprocesses)
        self.verbose_level = self.verbose_level
        return original_stdout

    def _run_simulation_engine(self, start_new_process):
        """Method that creates a simulation engine in a context (with ...) and runs a simulation.
        Args:
            start_new_process (bool, optional): A flag passed to the engine
                so it knows if it is running in a subprocess.
        Returns:
            obj:SimulationOutput : The output of the simulation run.
        """

        with SimulationEngine(self) as se:
            se.new_process = start_new_process
            se.init_only = self.init_only
            output = se.run_engine()
        return output

    def run(self, start_new_process=False):
        # if windows and MT -> fail
        if os.name == "nt" and self.multithreaded:
            fatal(
                "Error, the multi-thread option is not available for Windows now. "
                "Run the simulation with one thread."
            )

        # prepare the subprocess
        if start_new_process is True:
            """Important: put:
                if __name__ == '__main__':
                at the beginning of the script
            https://britishgeologicalsurvey.github.io/science/python-forking-vs-spawn/
            """

            logger.info("Dispatching simulation to subprocess ...")
            output = dispatch_to_subprocess(self._run_simulation_engine, True)

            # Recover output from unpickled actors coming from the subprocess queue
            for actor in self.actor_manager.actors.values():
                actor.recover_user_output(output.get_actor(actor.name))

            # FIXME: temporary workaround to copy from output the additional
            # information of the source (such as fTotalSkippedEvents)
            s = {}
            for source in self.source_manager.sources.values():
                # WARNING: when multithread, the sources are stored in
                # simulation_output.sources_by_thread
                # The sources of thread=0 are also available in simulation_output.sources
                # and they are retrieved here by get_source
                try:
                    s = output.get_source(source.name)
                except:
                    continue
                if "total_zero_events" in s.__dict__:
                    source.total_zero_events = s.__dict__["total_zero_events"]
                    source.total_skipped_events = s.__dict__["total_skipped_events"]
                if "particle_generators" in s.__dict__:
                    source.particle_generators = s.__dict__["particle_generators"]
                    source.num_entries = s.__dict__["num_entries"]

        else:
            # Nothing special to do if the simulation engine ran in the native python process
            # because everything is already in place.
            output = self._run_simulation_engine(False)

        # replace warnings by the one of the subprocess
        self._user_warnings = output.warnings

        # save the log output
        self.log_output = output.log_output

        # FIXME workaround
        self.expected_number_of_events = output.expected_number_of_events

        # store the hook log
        self.user_hook_log = output.user_hook_log
        self._current_random_seed = output.current_random_seed

        if self.store_json_archive is True:
            self.to_json_file()

        # FIXME: MaterialDatabase should become a Manager/Engine with close mechanism
        if self.volume_manager.material_database is None:
            self.volume_manager.material_database = MaterialDatabase()

        # print the warnings (if the logger level is ok)
        if log_level(self.log_handler_id) < WARNING:
            if len(self.warnings) > 0:
                if len(self.warnings) == 1:
                    warning(f"One warning occurred in this simulation:")
                else:
                    warning(
                        f"{len(self.warnings)} warnings occurred in this simulation:"
                    )
                for i, w in enumerate(self.warnings):
                    warning(f"({i+1}) {w}")

        # For all biasing operators inheriting from G4VBiasingOperator,
        # we need to clean the global static variable "fOperators" once everything is done
        #  to be able to start another simulation. This should be only once,
        # and for any one of the operators, we choose GateGammaFreeFlightOptrActor
        # but this cleans for all. Trust me, bro.
        g4.GateGammaFreeFlightOptrActor.ClearOperators()

    def voxelize_geometry(
        self,
        extent="auto",
        spacing=(3, 3, 3),
        margin=0,
        filename=None,
        return_path=False,
    ):
        return voxelize_geometry(self, extent, spacing, margin, filename, return_path)

    def initialize_source_before_g4_engine(self):
        """
        Some sources need to perform computation once everything is defined in user_info, but *before* the
        initialization of the G4 engine starts. This can be done via this function.
        """
        self.source_manager.initialize_before_g4_engine()


def create_sim_from_json(path):
    sim = Simulation()
    sim.from_json_file(path)
    return sim


process_cls(PhysicsManager)
process_cls(PhysicsListManager)
process_cls(VolumeManager)
process_cls(ActorManager)
process_cls(PostProcessingManager)
process_cls(Simulation)
process_cls(SourceManager)
