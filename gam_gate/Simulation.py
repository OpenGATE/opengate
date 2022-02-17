from box import Box, BoxList
import gam_gate as gam
from gam_gate import log
import gam_g4 as g4
import time
import random
import sys
from .ExceptionHandler import *


class Simulation:
    """
    Main class that store and build a simulation.
    """

    def __init__(self, name='simulation'):
        """
        Constructor. Main members are:
        - managers of volumes, sources and actors
        - Geant4 objects that will be build during initialisation (start with g4_)
        - some internal variables
        """
        self.name = name

        # user's defined parameters
        self.user_info = gam.SimulationUserInfo(self)

        # main managers
        self.volume_manager = gam.VolumeManager(self)
        self.source_manager = gam.SourceManager(self)
        self.actor_manager = gam.ActorManager(self)
        self.physics_manager = gam.PhysicsManager(self)
        self.filter_manager = gam.FilterManager(self)
        self.action_manager = None  # will created later (need source)

        # G4 elements
        self.g4_RunManager = None
        self.g4_PhysList = None  # FIXME will be changed
        self.g4_HepRandomEngine = None
        self.g4_ui = None
        self.g4_exception_handler = None

        # internal state
        self.is_initialized = False
        self.run_timing_intervals = None
        self.ui_session = None
        self.actual_random_seed = None

        # default elements
        self._default_parameters()

    def __del__(self):
        # set verbose to zero before destructor
        if self.g4_RunManager:
            self.g4_RunManager.SetVerboseLevel(0)
        pass

    def __str__(self):
        i = 'initialized'
        if not self.is_initialized:
            i = f'not {i}'
        s = f'Simulation name: {self.name} ({i})\n' \
            f'Geometry       : {self.volume_manager}\n' \
            f'Physics        : {self.physics_manager}\n' \
            f'Sources        : {self.source_manager}\n' \
            f'Actors         : {self.actor_manager}'
        return s

    def _default_parameters(self):
        """
        Internal use.
        Build default elements: verbose, World, seed, physics, etc.
        """
        # World volume
        w = self.add_volume('Box', gam.__world_name__)
        w.mother = None
        m = gam.g4_units('meter')
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = 'G4_AIR'
        # run timing
        sec = gam.g4_units('second')
        self.run_timing_intervals = [[0 * sec, 1 * sec]]  # a list of begin-end time values

    def dump_sources(self):
        return self.source_manager.dump()

    def dump_source_types(self):
        s = f''
        for t in gam.source_builders:
            s += f'{t} '
        return s

    def dump_volumes(self):
        return self.volume_manager.dump()

    def dump_volume_types(self):
        s = f''
        for t in gam.volume_builders:
            s += f'{t} '
        return s

    def dump_actors(self):
        return self.actor_manager.dump()

    def dump_actor_types(self):
        s = f''
        for t in gam.actor_builders:
            s += f'{t} '
        return s

    def dump_material_database_names(self):
        return list(self.volume_manager.material_databases.keys())

    def dump_material_database(self, db, level=0):
        if db not in self.volume_manager.material_databases:
            gam.fatal(f'Cannot find the db "{db}" in the '
                      f'list: {self.dump_material_database_names()}')
        thedb = self.volume_manager.material_databases[db]
        if db == 'NIST':
            return thedb.GetNistMaterialNames()
        return thedb.dump_materials(level)

    def dump_defined_material(self, level=0):
        if not self.is_initialized:
            gam.fatal(f'Cannot dump defined material before initialisation')
        return self.volume_manager.dump_defined_material(level)

    def initialize(self):
        """
        Build the main geant4 objects and initialize them.
        """
        # shorter code
        ui = self.user_info

        # g4 verbose
        self.initialize_g4_verbose()

        # check multithreading
        mt = g4.GamInfo.get_G4MULTITHREADED()
        if ui.number_of_threads > 1 and not mt:
            gam.fatal('Cannot use multi-thread, gam_g4 was not compiled with Geant4 MT')

        # check if RunManager already exists (it should not)
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            rm = g4.G4MTRunManager.GetRunManager()
        else:
            rm = g4.G4RunManager.GetRunManager()
        if rm:
            s = f'Cannot create a Simulation, the G4RunManager already exist.'
            gam.fatal(s)

        # init random engine (before the MTRunManager creation)
        self.initialize_random_engine()

        # create the RunManager
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            log.info(f'Simulation: create G4MTRunManager with {ui.number_of_threads} threads')
            rm = g4.G4MTRunManager()
            rm.SetNumberOfThreads(ui.number_of_threads)
        else:
            log.info('Simulation: create G4RunManager')
            rm = g4.G4RunManager()
        self.g4_RunManager = rm
        self.g4_RunManager.SetVerboseLevel(ui.g4_verbose_level)

        # Cannot be initialized two times (ftm)
        if self.is_initialized:
            gam.fatal('Simulation already initialized. Abort')

        # create the handler for the exception
        self.g4_exception_handler = ExceptionHandler()

        # check run timing
        gam.assert_run_timing(self.run_timing_intervals)

        # geometry
        log.info('Simulation: initialize Geometry')
        self.g4_RunManager.SetUserInitialization(self.volume_manager)

        # phys
        log.info('Simulation: initialize Physics')
        self.physics_manager.initialize()
        self.g4_RunManager.SetUserInitialization(self.physics_manager.g4_physic_list)

        # sources
        log.info('Simulation: initialize Source')
        self.source_manager.run_timing_intervals = self.run_timing_intervals
        self.source_manager.initialize(self.run_timing_intervals)

        # action
        log.info('Simulation: initialize Actions')
        self.action_manager = gam.ActionManager(self.source_manager)
        self.g4_RunManager.SetUserInitialization(self.action_manager)

        # Actors initialization (before the RunManager Initialize)
        self.actor_manager.create_actors(self.action_manager)

        # Initialization
        log.info('Simulation: initialize G4RunManager')
        self.g4_RunManager.Initialize()
        self.is_initialized = True

        # Physics initialization
        self.physics_manager.initialize_cuts()

        # Actors initialization
        log.info('Simulation: initialize Actors')
        self.actor_manager.initialize()

        # Check overlaps
        if ui.check_volumes_overlap:
            log.info('Simulation: check volumes overlap')
            self.check_volumes_overlap(verbose=False)

        # Register sensitive detector.
        # if G4 was compiled with MT (regardless it is used or not)
        # ConstructSDandField (in VolumeManager) will be automatically called
        if not g4.GamInfo.get_G4MULTITHREADED():
            gam.warning('DEBUG Register sensitive detector in no MT mode')
            self.actor_manager.register_sensitive_detectors()

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.is_initialized:
            gam.fatal(f'Please, use g4_apply_command *after* simulation.initialize()')
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    def start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        if not self.is_initialized:
            gam.fatal('Use "initialize" before "start"')
        log.info('-' * 80 + '\nSimulation: START')

        # FIXME check run_timing_intervals

        # visualisation should be initialized *after* other initializations
        # FIXME self._initialize_visualisation()

        # actor: start simulation (only the master thread)
        self.actor_manager.start_simulation()

        # go !
        start = time.time()
        self.source_manager.start()
        end = time.time()

        # actor: stop simulation (only the master thread)
        self.actor_manager.stop_simulation()

        # this is the end
        log.info(f'Simulation: STOP. Run: {len(self.run_timing_intervals)}. '
                 # f'Events: {self.source_manager.total_events_count}. '
                 f'Time: {end - start:0.1f} seconds.\n'
                 + f'-' * 80)

    def initialize_random_engine(self):
        # FIXME add more random engine later
        engine_name = self.user_info.random_engine
        self.g4_HepRandomEngine = None
        if engine_name == 'MixMaxRng':
            self.g4_HepRandomEngine = g4.MixMaxRng()
        if engine_name == 'MersenneTwister':
            self.g4_HepRandomEngine = g4.MTwistEngine()
        if not self.g4_HepRandomEngine:
            s = f'Cannot find the random engine {engine_name}\n'
            s += f'Use: MersenneTwister or MixMaxRng'
            gam.fatal(s)

        # set the random engine
        g4.G4Random.setTheEngine(self.g4_HepRandomEngine)
        if self.user_info.random_seed == 'auto':
            self.actual_random_seed = random.randrange(sys.maxsize)
        else:
            self.actual_random_seed = self.user_info.random_seed

        # set the seed
        g4.G4Random.setTheSeeds(self.actual_random_seed, 0)

    def initialize_g4_verbose(self):
        # For a unknow reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        ui = None
        if not self.user_info.g4_verbose:
            # no Geant4 output
            ui = gam.UIsessionSilent()
        else:
            # Geant4 output with color
            ui = gam.UIsessionVerbose()
        # it is also possible to set ui=None for 'default' output
        self.set_g4_ui_output(ui)

    def set_g4_ui_output(self, ui_session):
        # we must kept a ref to ui_session
        self.ui_session = ui_session
        # we must kept a ref to ui_manager
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.SetCoutDestination(ui_session)

    @property
    def world(self):
        return self.get_volume_user_info(gam.__world_name__)

    def get_volume_user_info(self, name):
        v = self.volume_manager.get_volume_info(name)
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
        s = self.actor_manager.get_actor(name)
        return s.user_info

    def get_actor(self, name):
        if not self.is_initialized:
            gam.fatal(f'Cannot get an actor before initialization')
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

    def check_volumes_overlap(self, verbose=True):
        if not self.is_initialized:
            gam.fatal(f'Cannot check overlap: the simulation must be initialized before')
        # FIXME: later, allow to bypass this check ?
        # FIXME: How to manage the verbosity ?
        b = self.user_info.g4_verbose
        self.user_info.g4_verbose = True
        self.initialize_g4_verbose()
        self.volume_manager.check_overlaps(verbose)
        self.user_info.g4_verbose = b
        self.initialize_g4_verbose()
