from .ExceptionHandler import *


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

        # user's defined parameters
        self.user_info = gate.SimulationUserInfo(self)
        self.run_timing_intervals = None

        # list of G4 commands that will be called after
        # initialization and before start
        self.g4_commands = []

        # main managers
        self.volume_manager = gate.VolumeManager(self)
        self.source_manager = gate.SourceManager(self)
        self.actor_manager = gate.ActorManager(self)
        self.physics_manager = gate.PhysicsManager(self)
        self.filter_manager = gate.FilterManager(self)

        # default elements
        self._default_parameters()

        # output of the simulation (once run)
        self.output = None

        # hook functions
        self.user_fct_after_init = None

        # for debug only
        self.verbose_destructor = False
        self.verbose_getstate = False
        self.verbose_close = False

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting Simulation")

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
        for t in gate.source_builders:
            s += f"{t} "
        return s

    def dump_volumes(self):
        return self.volume_manager.dump_volumes()

    def dump_tree_of_volumes(self):
        return self.volume_manager.dump_tree_of_volumes().encode("utf-8")

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
        return list(self.volume_manager.material_database.filenames)

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        self.g4_commands.append(command)

    @property
    def world(self):
        return self.get_volume_user_info(gate.__world_name__)

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

    def set_production_cut(self, volume_name, particle_name, value):
        self.physics_manager.set_production_cut(volume_name, particle_name, value)

    # keep old function for compatibility
    def set_cut(self, volume_name, particle, value):
        if volume_name == gate.__world_name__:
            self.physics_manager.global_production_cuts[particle] = value
        else:
            self.set_production_cut(volume_name, particle, value)

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

    def set_physics_list(self, pl):
        p = self.get_physics_user_info()
        p.physics_list_name = pl

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

    def check_geometry(self):
        names = {}
        volumes = self.volume_manager.volumes_user_info
        for v in volumes:
            vol = volumes[v]

            # volume must have a name
            if "_name" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'name' : {vol}")

            # volume name must be geometry name
            if v != vol.name:
                gate.fatal(
                    f"Volume named '{v}' in geometry has a different name : {vol}"
                )

            if vol.name in names:
                gate.fatal(f"Two volumes have the same name '{vol.name}' --> {self}")
            names[vol.name] = True

            # volume must have a mother
            if "mother" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'mother' : {vol}")

            # volume must have a material
            if "material" not in vol.__dict__:
                gate.fatal(f"Volume is missing a 'material' : {vol}")

    def create_region(self, name):
        return self.physics_manager.create_region(name)

    def initialize(self):
        # self.current_engine = gate.SimulationEngine(self, start_new_process=False)
        gate.warning(f"(initialization do nothing)")

    def start(self, start_new_process=False):
        se = gate.SimulationEngine(self, start_new_process=start_new_process)
        return se.start()

    @property
    def use_multithread(self):
        return (
            self.user_info.number_of_threads > 1
            or self.user_info.force_multithread_mode
        )

    def run(self, start_new_process=False):
        # Context manager currently only works if no new process is started.
        if start_new_process is False:
            with gate.SimulationEngine(self, start_new_process=start_new_process) as se:
                self.output = se.start()
        else:
            se = gate.SimulationEngine(self, start_new_process=start_new_process)
            self.output = se.start()
