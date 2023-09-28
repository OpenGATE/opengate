import sys
from copy import copy
from box import Box

import opengate_core as g4

from .base import GateObject, GateObjectSingleton
from .definitions import __world_name__
from .element import new_element
from .engines import SimulationEngine
from .exception import fatal, warning
from .geometry.BooleanVolume import bool_operators
from .geometry.materials import MaterialDatabase
from .geometry.utility import build_tree, render_tree
from .utility import (
    assert_unique_element_name,
    g4_units,
    indent,
    read_mac_file_to_commands,
)
from .logger import INFO, log
from .physics import Region, cut_particle_names
from .userinfo import UserInfo


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

    def __del__(self):
        if self.simulation.verbose_destructor:
            warning("Deleting FilterManager")

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
        if name not in self.filters:
            fatal(
                f"The Filter {name} is not in the current "
                f"list of Filters: {self.filters}"
            )
        return self.filters[name]

    def add_filter(self, filter_type, name):
        # check that another element with the same name does not already exist
        assert_unique_element_name(self.filters, name)
        # build it
        a = UserInfo("Filter", filter_type, name)
        # append to the list
        self.user_info_filters[name] = a
        # return the info
        return a

    def initialize(self):
        for ui in self.user_info_filters.values():
            filter = new_element(ui, self.simulation)
            log.debug(f"Filter: initialize [{ui.type_name}] {ui.name}")
            filter.Initialize(ui)
            self.filters[ui.name] = filter


class SourceManager:
    """
    Manage all the sources in the simulation.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    def __init__(self, simulation):
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # List of run times intervals
        self.run_timing_intervals = None
        self.current_run_interval = None
        # List of sources user info
        self.user_info_sources = {}

    def __str__(self):
        """
        str only dump the user info on a single line
        """
        v = [v.name for v in self.user_info_sources.values()]
        s = f'{" ".join(v)} ({len(self.user_info_sources)})'
        return s

    def __del__(self):
        if self.simulation.verbose_destructor:
            warning("Deleting SourceManager")

    def dump(self):
        n = len(self.user_info_sources)
        s = f"Number of sources: {n}"
        for source in self.user_info_sources.values():
            a = f"\n {source}"
            s += indent(2, a)
        return s

    def get_source_info(self, name):
        if name not in self.user_info_sources:
            fatal(
                f"The source {name} is not in the current "
                f"list of sources: {self.user_info_sources}"
            )
        return self.user_info_sources[name]

    """def get_source(self, name):
        n = len(self.g4_thread_source_managers)
        if n > 0:
            gate.exception.warning(f"Cannot get source in multithread mode, use get_source_MT")
            return None
        for source in self.sources:
            if source.user_info.name == name:
                return source.g4_source
        gate.exception.fatal(
            f'The source "{name}" is not in the current '
            f"list of sources: {self.user_info_sources}"
        )

    def get_source_MT(self, name, thread):
        n = len(self.g4_thread_source_managers)
        if n == 0:
            gate.exception.warning(f"Cannot get source in mono-thread mode, use get_source")
            return None
        i = 0
        for source in self.sources:
            if source.user_info.name == name:
                if i == thread:
                    return source.g4_source
                i += 1
        gate.exception.fatal(
            f'The source "{name}" is not in the current '
            f"list of sources: {self.user_info_sources}"
        )"""

    def add_source(self, source_type, name):
        # check that another element with the same name does not already exist
        assert_unique_element_name(self.user_info_sources, name)
        # init the user info
        s = UserInfo("Source", source_type, name)
        # append to the list
        self.user_info_sources[name] = s
        # return the info
        return s


class ActorManager:
    """
    Manage all the actors in the simulation
    """

    def __init__(self, simulation):
        self.simulation = simulation
        self.user_info_actors = {}

    def __str__(self):
        v = [v.name for v in self.user_info_actors.values()]
        s = f'{" ".join(v)} ({len(self.user_info_actors)})'
        return s

    def __del__(self):
        if self.simulation.verbose_destructor:
            warning("Deleting ActorManager")

    """def __getstate__(self):
        if self.simulation.verbose_getstate:
            gate.exception.warning("Getstate ActorManager")
        # needed to not pickle. Need to reset user_info_actors to avoid to store the actors
        self.user_info_actors = {}
        return self.__dict__"""

    def dump(self):
        n = len(self.user_info_actors)
        s = f"Number of Actors: {n}"
        for actor in self.user_info_actors.values():
            if n > 1:
                a = "\n" + "-" * 20
            else:
                a = ""
            a += f"\n {actor}"
            s += indent(2, a)
        return s

    def get_actor_user_info(self, name):
        if name not in self.user_info_actors:
            fatal(
                f"The actor {name} is not in the current "
                f"list of actors: {self.user_info_actors}"
            )
        return self.user_info_actors[name]

    def add_actor(self, actor_type, name):
        # check that another element with the same name does not already exist
        assert_unique_element_name(self.user_info_actors, name)
        # build it
        a = UserInfo("Actor", actor_type, name)
        # append to the list
        self.user_info_actors[name] = a
        # return the info
        return a


class PhysicsListManager(GateObjectSingleton):
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
    special_physics_constructor_classes[
        "G4RadioactiveDecayPhysics"
    ] = g4.G4RadioactiveDecayPhysics
    special_physics_constructor_classes["G4OpticalPhysics"] = g4.G4OpticalPhysics
    special_physics_constructor_classes["G4EmDNAPhysics"] = g4.G4EmDNAPhysics

    def __init__(self, physics_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.physics_manager = physics_manager
        # declare the attribute here as None;
        # set to dict in create_physics_list_classes()
        self.created_physics_list_classes = None
        self.create_physics_list_classes()

    def __getstate__(self):
        # This is needed because cannot be pickled.
        dict_to_return = dict([(k, v) for k, v in self.__dict__.items()])
        dict_to_return["created_physics_list_classes"] = None
        return dict_to_return

    def __setstate__(self, d):
        self.__dict__ = d
        self.create_physics_list_classes()

    def create_physics_list_classes(self):
        self.created_physics_list_classes = {}
        for g4pc_name in self.available_g4_physics_constructors:
            self.created_physics_list_classes[
                g4pc_name
            ] = create_modular_physics_list_class(g4pc_name)

    def get_physics_list(self, physics_list_name):
        if physics_list_name in self.created_physics_list_classes:
            physics_list = self.created_physics_list_classes[physics_list_name](
                self.physics_manager.simulation.user_info.g4_verbose_level
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
        ) in self.physics_manager.user_info.special_physics_constructors.items():
            if switch is True:
                try:
                    physics_list.ReplacePhysics(
                        self.special_physics_constructor_classes[spc](
                            self.physics_manager.simulation.user_info.g4_verbose_level
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

    # # names for particle cuts
    # cut_particle_names = {
    #     "gamma": "gamma",
    #     "electron": "e-",
    #     "positron": "e+",
    #     "proton": "proton",
    # }

    user_info_defaults = {}
    user_info_defaults["physics_list_name"] = (
        "QGSP_BERT_EMV",
        {"doc": "Name of the Geant4 physics list. "},
    )
    user_info_defaults["global_production_cuts"] = (
        Box([("all", None)] + [(pname, None) for pname in cut_particle_names]),
        {
            "doc": "Dictionary containing the production cuts (range) for gamma, electron, positron, proton. Option 'all' overrides individual cuts."
        },
    )
    user_info_defaults["apply_cuts"] = (
        True,
        {"doc": "Flag to turn of cuts 'on the fly'. Still under development in Gate."},
    )
    user_info_defaults["energy_range_min"] = (
        None,
        {
            "doc": "Minimum energy for secondary particle production. If None, physics list default is used."
        },
    )
    user_info_defaults["energy_range_max"] = (
        None,
        {
            "doc": "Maximum energy for secondary particle production. If None, physics list default is used."
        },
    )
    user_info_defaults["user_limits_particles"] = (
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
    )
    user_info_defaults["em_parameters"] = (
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
    )
    user_info_defaults["em_switches_world"] = (
        Box([("deex", None), ("auger", None), ("pixe", None)]),
        {
            "doc": "Switch on/off EM parameters in the world region.",
            "expose_items": False,
        },
    )

    # user_info_defaults["enable_decay"] = (
    #     False,
    #     {"doc": "Will become obsolete after PR 187 is merged. "},
    # )

    user_info_defaults["special_physics_constructors"] = (
        Box(
            [
                (spc, False)
                for spc in PhysicsListManager.special_physics_constructor_classes
            ]
        ),
        {
            "doc": "Special physics constructors to be added to the physics list, e.g. G4Decay, G4OpticalPhysics. "
        },
    )

    def __init__(self, simulation, *args, **kwargs):
        super().__init__(name="physics_manager", *args, **kwargs)

        # Keep a pointer to the current simulation
        self.simulation = simulation
        self.physics_list_manager = PhysicsListManager(self, name="PhysicsListManager")

        # dictionary containing all the region objects
        # key=region_name, value=region_object
        self.regions = {}
        # Dictionary to quickly find the region to which a volume is associated.
        # This dictionary is updated by the region's associate_volume method.
        # Do not update manually!
        # key=volume_name, value=region=object
        # NB: It is well-defined because each volume has only one region.
        self.volumes_regions_lut = {}

    def __str__(self):
        s = ""
        for k, v in self.user_info.items():
            s += f"{k}: {v}\n"
        return s

    def __getstate__(self):
        if self.simulation.verbose_getstate:
            warning("Getstate PhysicsManager")

        dict_to_return = dict([(k, v) for k, v in self.__dict__.items()])
        dict_to_return["physics_list_manager"] = None
        return dict_to_return

    def __setstate__(self, d):
        self.__dict__ = d
        self.physics_list_manager = PhysicsListManager(self, name="PhysicsListManager")

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
            s += f"*** Production cuts per regions ***\n"
            for region in self.regions.values():
                s += f"In region {region.name}:\n"
                s += region.dump_production_cuts()
        else:
            s += "*** No cuts per region defined. ***\n"
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

    def create_region(self, name):
        if name in self.regions.keys():
            fatal("A region with this name already exists.")
        self.regions[name] = Region(name=name)
        self.regions[name].physics_manager = self
        return self.regions[name]

    def find_or_create_region(self, volume_name):
        if volume_name not in self.volumes_regions_lut.keys():
            region = self.create_region(volume_name + "_region")
            region.associate_volume(volume_name)
        else:
            region = self.volumes_regions_lut[volume_name]
        return region

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


class VolumeManager:
    """
    Store and manage a hierarchical list of geometrical volumes and associated materials.
    This tree will be converted into Geant4 Solid/PhysicalVolume/LogicalVolumes
    """

    def __init__(self, simulation):
        """
        Class that store geometry description.
        """
        self.simulation = simulation

        # world name by default (will be changed if parallel world)
        self.world_name = __world_name__

        # list of all parallel worlds (must be ordered)
        self.parallel_world_names = []

        # list of all user_info describing the volumes
        self.volumes_user_info = {}  # user info only

        # database of materials
        self.material_database = MaterialDatabase()

    def __del__(self):
        if self.simulation.verbose_destructor:
            warning("Deleting VolumeManager")

    def __str__(self):
        s = f"{len(self.volumes_user_info)} volumes"
        return s

    def _simulation_engine_closing(self):
        """
        This function should be called from the simulation engine
        when it is closing to make sure that G4 references are set to None.
        """
        self.material_database = None
        # self.volumes_user_info = None

    def get_volume_user_info(self, name):
        if name not in self.volumes_user_info:
            fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.volumes_user_info}"
            )
        return self.volumes_user_info[name]

    def new_solid(self, solid_type, name):
        from .userelement import _pop_keys_unused_by_solid
        from .userinfo import UserInfo

        if solid_type == "Boolean":
            fatal(f"Cannot create solid {solid_type}")
        # Create a UserInfo for a volume
        u = UserInfo("Volume", solid_type, name)
        # remove unused keys: object, etc. (it's a solid, not a volume)
        _pop_keys_unused_by_solid(u)
        return u

    def get_solid_info(self, user_info):
        """
        Temporary build a solid from the user info, in order to retrieve information (volume etc).
        Can be used *before* initialization
        """
        from .element import new_element

        vol = new_element(user_info, self.simulation)
        vol = vol.build_solid()
        r = Box()
        r.cubic_volume = vol.GetCubicVolume()
        r.surface_area = vol.GetSurfaceArea()
        pMin = g4.G4ThreeVector()
        pMax = g4.G4ThreeVector()
        vol.BoundingLimits(pMin, pMax)
        r.bounding_limits = [pMin, pMax]
        return r

    def get_volume_depth(self, volume_name):
        depth = 0
        current = self.get_volume_user_info(volume_name)
        while current.name != "world":
            current = self.get_volume_user_info(current.mother)
            depth += 1
        return depth

    def add_parallel_world(self, name):
        if name in self.parallel_world_names:
            fatal(
                f"Cannot create the parallel world named {name} because it already exists"
            )
        self.parallel_world_names.append(name)

    def get_volume_world(self, volume_name):
        vol = self.get_volume_user_info(volume_name)
        if vol.mother is None or vol.mother == self.world_name:
            return self.world_name
        if vol.mother in self.parallel_world_names:
            return vol.mother
        if volume_name not in self.volumes_user_info:
            fatal(f"Cannot find the volume {volume_name}")
        return self.get_volume_world(vol.mother)

    def add_volume(self, vol_type, name):
        # check that another element with the same name does not already exist
        assert_unique_element_name(self.volumes_user_info, name)
        # initialize the user_info
        v = UserInfo("Volume", vol_type, name)
        # add to the list
        self.volumes_user_info[name] = v
        # FIXME  NOT CLEAR --> here ? or later
        # create a region for the physics cuts
        # user will be able to set stuff like :
        # pm.production_cuts.my_volume.gamma = 1 * mm
        # pm = self.simulation.get_physics_user_info()
        # pm.production_cuts[name] = Box()
        # return the info
        return v

    def add_volume_from_solid(self, solid, name):
        v = None
        for op in bool_operators:
            try:
                if op in solid:
                    v = self.add_volume("Boolean", name)
                    v.solid = solid
            except:
                pass
        if not v:
            v = self.add_volume(solid.type_name, name)
            # copy the parameters of the solid
            # FIXME: not needed after volume refactoring
            from .element import copy_user_info

            copy_user_info(solid, v)
        return v

    def add_material_database(self, filename):
        if filename in self.material_database.filenames:
            fatal(f'Database "{filename}" already exist.')
        self.material_database.read_from_file(filename)

    def dump_volumes(self):
        s = f"Number of volumes: {len(self.volumes_user_info)}"
        for vol in self.volumes_user_info.values():
            s += indent(2, f"\n{vol}")
        return s

    def separate_parallel_worlds(self):
        world_volumes_user_info = {}
        # init list of trees
        world_volumes_user_info[self.world_name] = {}
        for w in self.parallel_world_names:
            world_volumes_user_info[w] = {}

        # loop to separate volumes for each world
        uiv = self.volumes_user_info
        for vu in uiv.values():
            world_name = self.get_volume_world(vu.name)
            world_volumes_user_info[world_name][vu.name] = vu

        # add a 'fake' copy of the real world volume to each parallel world
        # this is needed for build_tre
        the_world = world_volumes_user_info[__world_name__][__world_name__]
        for w in self.parallel_world_names:
            a = copy(the_world)
            a._name = w
            world_volumes_user_info[w][w] = a
        return world_volumes_user_info

    def dump_tree_of_volumes(self):  # FIXME put elsewhere
        world_volumes_user_info = self.separate_parallel_worlds()
        s = ""
        for w in world_volumes_user_info:
            vui = world_volumes_user_info[w]
            tree = build_tree(vui, w)
            info = {}
            for v in vui.values():
                info[v.name] = v
            s += render_tree(tree, info, w) + "\n"
        # remove last line break
        s = s[:-1]
        return s


class SimulationUserInfo:
    """
    This class is a simple structure that contains all user general options of a simulation.
    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # gate (pre-run) verbose
        # A number or gate.NONE or gate.INFO or gate.DEBUG
        self._verbose_level = INFO
        log.setLevel(self._verbose_level)

        # gate verbose during running
        self.running_verbose_level = 0

        # Geant4 verbose
        # For an unknown reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        self.g4_verbose_level = 1
        self.g4_verbose = False

        # visualisation (qt|vrml)
        self.visu = False
        # visu_type choice: "qt" "vrml" "gdml" "gdml_file_onlu" "vrml_file_only"
        self.visu_type = "qt"
        self.visu_filename = None
        self.visu_verbose = False
        self.visu_commands = read_mac_file_to_commands("default_visu_commands.mac")
        self.visu_commands_vrml = read_mac_file_to_commands(
            "default_visu_commands_vrml.mac"
        )
        self.visu_commands_gdml = read_mac_file_to_commands(
            "default_visu_commands_gdml.mac"
        )

        # check volume overlap once constructed
        self.check_volumes_overlap = True

        # multi-threading
        self.number_of_threads = 1
        self.force_multithread_mode = False

        # random engine
        # MixMaxRng seems recommended for MultiThread
        self.random_engine = "MixMaxRng"  # 'MersenneTwister'
        self.random_seed = "auto"

    @property
    def verbose_level(self):
        return self._verbose_level

    @verbose_level.setter
    def verbose_level(self, value):
        log.setLevel(value)
        self._verbose_level = value

    def __del__(self):
        pass

    def __str__(self):
        if self.number_of_threads == 1 and not self.force_multithread_mode:
            g = g4.GateInfo.get_G4MULTITHREADED()
            t = "no"
            if g:
                t += " (but available: G4 was compiled with MT)"
            else:
                t += " (not available, G4 was not compiled with MT)"
        else:
            t = f"{self.number_of_threads} threads"
        s = (
            f"Verbose         : {self.verbose_level}\n"
            f"Running verbose : {self.running_verbose_level}\n"
            f"Geant4 verbose  : {self.g4_verbose}, level = {self.g4_verbose_level}\n"
            f"Visualisation   : {self.visu}, verbose level = {self.g4_verbose_level}\n"
            f"Visu type       : {self.visu_type}\n"
            f"Check overlap   : {self.check_volumes_overlap}\n"
            f"Multithreading  : {t}\n"
            f"Random engine   : {self.random_engine}, seed = {self.random_seed}"
        )
        return s


class Simulation:
    """
    Main class that store a simulation.
    It contains:
    - a set of global user parameters (SimulationUserInfo)
    - user parameters for Volume, Source, Actors and Filters, Physics
    - a list of g4 commands that will be set to G4 engine after the initialization

    There is NO Geant4 engine here, it is only a set of parameters and options.
    """

    def __init__(self, name="simulation"):
        """
        Main members are:
        - managers of volumes, physics, sources, actors and filters
        - the Geant4 objects will be only built during initialisation in SimulationEngine
        """
        self.name = name

        # for debug only
        self.verbose_destructor = False
        self.verbose_getstate = False
        self.verbose_close = False

        # user's defined parameters
        self.user_info = SimulationUserInfo(self)
        self.run_timing_intervals = None

        # list of G4 commands that will be called after
        # initialization and before start
        self.g4_commands = []
        self.g4_commands_before_init = []

        # main managers
        self.volume_manager = VolumeManager(self)
        self.source_manager = SourceManager(self)
        self.actor_manager = ActorManager(self)
        self.physics_manager = PhysicsManager(self)
        self.filter_manager = FilterManager(self)

        # default elements
        self._default_parameters()

        # output of the simulation (once run)
        self.output = None

        # hook functions
        self.user_fct_after_init = None
        self.user_hook_after_run = None

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting Simulation")

    def __str__(self):
        s = (
            f"Simulation name: {self.name} \n"
            f"Geometry       : {self.volume_manager}\n"
            f"Physics        : {self.physics_manager}\n"
            f"Sources        : {self.source_manager}\n"
            f"Actors         : {self.actor_manager}"
        )
        return s

    def _default_parameters(self):
        """
        Internal use.
        Build default elements: verbose, World, seed, physics, etc.
        """
        # World volume
        w = self.add_volume("Box", __world_name__)
        w.mother = None
        m = g4_units.m
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = "G4_AIR"
        # run timing
        sec = g4_units.s
        self.run_timing_intervals = [
            [0 * sec, 1 * sec]
        ]  # a list of begin-end time values

    @property
    def number_of_threads(self):
        return self.user_info.number_of_threads

    @number_of_threads.setter
    def number_of_threads(self, n):
        self.user_info.number_of_threads = n

    def dump_sources(self):
        return self.source_manager.dump()

    def dump_source_types(self):
        s = f""
        # FIXME: workaround to avoid circular import, will be solved when refactoring sources
        from opengate.sources.builders import source_builders

        for t in source_builders:
            s += f"{t} "
        return s

    def dump_volumes(self):
        return self.volume_manager.dump_volumes()

    def dump_tree_of_volumes(self):
        return self.volume_manager.dump_tree_of_volumes().encode("utf-8")

    def dump_volume_types(self):
        s = f""
        # FIXME: workaround will become obsolete when volumes are refactored
        from opengate.geometry.builders import volume_builders

        for t in volume_builders:
            s += f"{t} "
        return s

    def dump_actors(self):
        return self.actor_manager.dump()

    def dump_actor_types(self):
        s = f""
        # FIXME: workaround to avoid circular import, will be solved when refactoring actors
        from opengate.actors.actorbuilders import actor_builders

        for t in actor_builders:
            s += f"{t} "
        return s

    def dump_material_database_names(self):
        return list(self.volume_manager.material_database.filenames)

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        self.g4_commands.append(command)

    def apply_g4_command_before_init(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        self.g4_commands_before_init.append(command)

    @property
    def world(self):
        return self.get_volume_user_info(__world_name__)

    def get_volume_user_info(self, name):
        v = self.volume_manager.get_volume_user_info(name)
        return v

    def get_all_volumes_user_info(self):
        return self.volume_manager.volumes_user_info

    def get_solid_info(self, user_info):
        return self.volume_manager.get_solid_info(user_info)

    def get_source_user_info(self, name):
        return self.source_manager.get_source_info(name)

    def get_actor_user_info(self, name):
        s = self.actor_manager.get_actor_user_info(name)
        return s

    def get_physics_user_info(self):
        return self.physics_manager.user_info

    def set_physics_list(self, phys_list, enable_decay=False):
        self.physics_manager.physics_list_name = phys_list
        self.physics_manager.enable_decay = enable_decay

    def get_physics_list(self):
        return self.physics_manager.physics_list_name

    def enable_decay(self, enable_decay):
        self.physics_manager.enable_decay = enable_decay

    def set_production_cut(self, volume_name, particle_name, value):
        self.physics_manager.set_production_cut(volume_name, particle_name, value)

    @property
    def global_production_cuts(self):
        return self.physics_manager.global_production_cuts

    # functions related to user limits
    def set_max_step_size(self, volume_name, max_step_size):
        self.physics_manager.set_max_step_size(volume_name, max_step_size)

    def set_max_track_length(self, volume_name, max_track_length):
        self.physics_manager.set_max_track_length(volume_name, max_track_length)

    def set_min_ekine(self, volume_name, min_ekine):
        self.physics_manager.set_min_ekine(volume_name, min_ekine)

    def set_max_time(self, volume_name, max_time):
        self.physics_manager.set_max_time(volume_name, max_time)

    def set_min_range(self, volume_name, min_range):
        self.physics_manager.set_min_range(volume_name, min_range)

    def set_user_limits_particles(self, particle_names):
        self.physics_manager.set_user_limits_particles(particle_names)

    def new_solid(self, solid_type, name):
        return self.volume_manager.new_solid(solid_type, name)

    def add_volume(self, solid_type, name):
        return self.volume_manager.add_volume(solid_type, name)

    def add_parallel_world(self, name):
        self.volume_manager.add_parallel_world(name)

    def add_volume_from_solid(self, solid, name):
        return self.volume_manager.add_volume_from_solid(solid, name)

    def add_source(self, source_type, name):
        return self.source_manager.add_source(source_type, name)

    def add_actor(self, actor_type, name):
        return self.actor_manager.add_actor(actor_type, name)

    def add_filter(self, filter_type, name):
        return self.filter_manager.add_filter(filter_type, name)

    def add_region(self, name):
        return self.physics_manager.create_region(name)

    def add_material_database(self, filename):
        self.volume_manager.add_material_database(filename)

    def add_material_nb_atoms(self, *kwargs):
        """
        Usage example:
        "Lead", ["Pb"], [1], 11.4 * gcm3
        "BGO", ["Bi", "Ge", "O"], [4, 3, 12], 7.13 * gcm3)
        """
        self.volume_manager.material_database.add_material_nb_atoms(kwargs)

    def add_material_weights(self, *kwargs):
        """
        Usage example :
        add_material_weights(name, elems_symbol_nz, weights_nz, 3 * gcm3)
        """
        self.volume_manager.material_database.add_material_weights(kwargs)

    def check_geometry(self):
        names = {}
        volumes = self.volume_manager.volumes_user_info
        for v in volumes:
            vol = volumes[v]

            # volume must have a name
            if "_name" not in vol.__dict__:
                fatal(f"Volume is missing a 'name' : {vol}")

            # volume name must be geometry name
            if v != vol.name:
                fatal(f"Volume named '{v}' in geometry has a different name : {vol}")

            if vol.name in names:
                fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother
            if "mother" not in vol.__dict__:
                fatal(f"Volume is missing a 'mother' : {vol}")

            # volume must have a material
            if "material" not in vol.__dict__:
                fatal(f"Volume is missing a 'material' : {vol}")

    def create_region(self, name):
        return self.physics_manager.create_region(name)

    def initialize(self):
        # self.current_engine = gate.SimulationEngine(self, start_new_process=False)
        warning(f"(initialization do nothing)")

    def start(self, start_new_process=False):
        se = SimulationEngine(self, start_new_process=start_new_process)
        self.output = se.start()
        return self.output

    @property
    def use_multithread(self):
        return (
            self.user_info.number_of_threads > 1
            or self.user_info.force_multithread_mode
        )

    def run(self, start_new_process=False):
        # Context manager currently only works if no new process is started.
        if start_new_process is False:
            with SimulationEngine(self, start_new_process=False) as se:
                self.output = se.start()
        else:
            se = SimulationEngine(self, start_new_process=start_new_process)
            self.output = se.start()
        return self.output
