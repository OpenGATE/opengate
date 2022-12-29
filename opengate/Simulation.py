from .ExceptionHandler import *


class Simulation:
    """
    Main class that store and build a simulation.
    """

    def __init__(self, name="simulation"):
        """
        Constructor. Main members are:
        - managers of volumes, sources and actors
        - Geant4 objects that will be build during initialisation (start with g4_)
        - some internal variables
        """
        self.name = name

        # user's defined parameters
        self.user_info = gate.SimulationUserInfo(self)
        self.run_timing_intervals = None

        # main managers
        self.volume_manager = gate.VolumeManager(self)
        self.source_manager = gate.SourceManager(self)
        self.actor_manager = gate.ActorManager(self)
        self.physics_manager = gate.PhysicsManager(self)
        self.filter_manager = gate.FilterManager(self)

        # default elements
        self._default_parameters()

    def __del__(self):
        print("del Simulation")
        pass

    def __str__(self):
        s = (
            f"Simulation name: {self.name} \n"
            f"Geometry       : {self.volume_manager}\n"
            f"Physics        : {self.physics_manager}\n"
            f"Sources        : {self.source_manager}\n"
            f"Actors         : {self.actor_manager}"
        )
        return s

    def __getstate__(self):
        del self.current_engine
        return self.__dict__

    def _default_parameters(self):
        """
        Internal use.
        Build default elements: verbose, World, seed, physics, etc.
        """
        # World volume
        w = self.add_volume("Box", gate.__world_name__)
        w.mother = None
        m = gate.g4_units("meter")
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = "G4_AIR"
        # run timing
        sec = gate.g4_units("second")
        self.run_timing_intervals = [
            [0 * sec, 1 * sec]
        ]  # a list of begin-end time values

    def dump_sources(self):
        return self.source_manager.dump()

    def dump_source_types(self):
        s = f""
        for t in gate.source_builders:
            s += f"{t} "
        return s

    def dump_volumes(self):
        return self.volume_manager.dump()

    def dump_volume_types(self):
        s = f""
        for t in gate.volume_builders:
            s += f"{t} "
        return s

    def dump_actors(self):
        return self.actor_manager.dump()

    def dump_actor_types(self):
        s = f""
        for t in gate.actor_builders:
            s += f"{t} "
        return s

    def dump_material_database_names(self):
        return list(self.volume_manager.user_material_databases.keys())

    def dump_material_database(self, db, level=0):
        if db not in self.volume_manager.user_material_databases:
            gate.fatal(
                f'Cannot find the db "{db}" in the '
                f"list: {self.dump_material_database_names()}"
            )
        thedb = self.volume_manager.user_material_databases[db]
        if db == "NIST":
            return thedb.GetNistMaterialNames()
        return thedb.dump_materials(level)

    def dump_defined_material(self, level=0):
        if not self.is_initialized:
            gate.fatal(f"Cannot dump defined material before initialisation")
        return self.volume_manager.dump_defined_material(level)

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.is_initialized:
            gate.fatal(f"Please, use g4_apply_command *after* simulation.initialize()")
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    @property
    def world(self):
        return self.get_volume_user_info(gate.__world_name__)

    def get_volume_user_info(self, name):
        v = self.volume_manager.get_volume_user_info(name)
        return v

    def get_all_volumes_user_info(self):
        return self.volume_manager.user_info_volumes

    def get_solid_info(self, user_info):
        return self.volume_manager.get_solid_info(user_info)

    def get_source_user_info(self, name):
        return self.source_manager.get_source_info(name)

    def get_source(self, name):
        return self.source_manager.get_source(name)

    def get_source_MT(self, name, thread):
        return self.source_manager.get_source_MT(name, thread)

    def get_actor_user_info(self, name):
        s = self.actor_manager.get_actor_user_info(name)
        return s

    def get_actor(self, name):
        if not self.is_initialized:
            gate.fatal(f"Cannot get an actor before initialization")
        return self.actor_manager.get_actor(name)

    def get_physics_user_info(self):
        return self.physics_manager.user_info

    def set_cut(self, volume_name, particle, value):
        self.physics_manager.set_cut(volume_name, particle, value)

    def set_physics_list(self, pl):
        p = self.get_physics_user_info()
        p.physics_list_name = pl

    def new_solid(self, solid_type, name):
        return self.volume_manager.new_solid(solid_type, name)

    def add_volume(self, solid_type, name):
        return self.volume_manager.add_volume(solid_type, name)

    def add_volume_from_solid(self, solid, name):
        return self.volume_manager.add_volume_from_solid(solid, name)

    def add_source(self, source_type, name):
        return self.source_manager.add_source(source_type, name)

    def add_actor(self, actor_type, name):
        return self.actor_manager.add_actor(actor_type, name)

    def add_filter(self, filter_type, name):
        return self.filter_manager.add_filter(filter_type, name)

    def add_material_database(self, filename, name=None):
        self.volume_manager.add_material_database(filename, name)

    """def check_volumes_overlap(self, verbose=True):
        if not self.is_initialized:
            gate.fatal(
                f"Cannot check overlap: the simulation must be initialized before"
            )
        # FIXME: later, allow to bypass this check ?
        # FIXME: How to manage the verbosity ?
        b = self.user_info.g4_verbose
        self.user_info.g4_verbose = True
        self.initialize_g4_verbose()
        self.volume_manager.check_overlaps(verbose)
        self.user_info.g4_verbose = b
        self.initialize_g4_verbose()"""

    def initialize(self):
        # self.current_engine = gate.SimulationEngine(self, spawn_process=False)
        gate.warning(f"(initialization do nothing)")

    def start(self):
        se = gate.SimulationEngine(self, spawn_process=False)
        return se.start()
