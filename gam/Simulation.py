from box import Box
import gam
from gam import log
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
        # FIXME replace by "options" or "settings"
        self.g4_verbose_level = 1
        self.g4_verbose = False
        self.g4_visualisation_options = Box()
        self.g4_multi_thread_flag = False
        self.number_of_initithreads = 2

        # main managers
        self.volume_manager = gam.VolumeManager(self)
        self.source_manager = gam.SourceManager(self)
        self.actor_manager = gam.ActorManager(self)
        self.action_manager = None  # will created later (need source)
        self.physics_manager = gam.PhysicsManager(self)

        # G4 elements
        self.g4_RunManager = None
        self.g4_PhysList = None  # FIXME will be changed
        self.g4_HepRandomEngine = None
        self.g4_ui = None
        self.g4_exception_handler = None

        # internal state
        self.initialized = False
        self.run_timing_intervals = None
        self.ui_session = None

        # default elements
        self._default_parameters()

    def __del__(self):
        # set verbose to zero before destructor
        if self.g4_RunManager:
            self.g4_RunManager.SetVerboseLevel(0)
        pass

    def __str__(self):
        i = 'initialized'
        if not self.initialized:
            i = f'not {i}'
        s = f'Simulation name: {self.name} ({i})\n' \
            f'Geometry       : {self.volume_manager}\n' \
            f'Physics        : {self.physics_info}\n' \
            f'Sources        : {self.source_manager}\n' \
            f'Actors         : {self.actor_manager}'
        return s

    def _default_parameters(self):
        """
        Internal use.
        Build default elements: verbose, World, seed, physics, etc.
        """
        # G4 output
        self.set_g4_verbose(False, 1)
        # MT
        self.g4_multi_thread_flag = False
        self.number_of_threads = 2
        # World volume
        w = self.add_volume('Box', 'World')
        w.mother = None
        m = gam.g4_units('meter')
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = 'G4_AIR'
        # seed
        self.seed = 'auto'
        # run timing
        sec = gam.g4_units('second')
        self.sim_time = 0 * sec
        self.run_timing_intervals = [[0 * sec, 1 * sec]]  # a list of begin-end time values
        # visu options # FIXME external class ?
        self.g4_visualisation_options.g4_visualisation_flag = False
        self.g4_visualisation_options.g4_visualisation_verbose_flag = False
        self.g4_visualisation_options.g4_vis_commands = gam.read_mac_file_to_commands('default_visu_commands.mac')

    def dump_sources(self, level=0):
        return self.source_manager.dump(level)

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
        if not self.initialized:
            gam.fatal(f'Cannot dump defined material before initialisation')
        return self.volume_manager.dump_defined_material(level)

    def initialize(self):
        """
        Build the main geant4 objects and initialize them.
        """
        # check if RunManager already exist
        if self.g4_multi_thread_flag:
            rm = g4.G4MTRunManager.GetRunManager()
        else:
            rm = g4.G4RunManager.GetRunManager()
        if rm:
            s = f'Cannot create a Simulation, the G4RunManager already exist.'
            gam.fatal(s)

        # create the RunManager
        if self.g4_multi_thread_flag:
            log.info(f'Simulation: create G4MTRunManager with {self.number_of_threads} threads')
            rm = g4.G4MTRunManager()
            rm.SetNumberOfThreads(self.number_of_threads)
        else:
            log.info('Simulation: create G4RunManager')
            rm = g4.G4RunManager()
        self.g4_RunManager = rm
        self.g4_RunManager.SetVerboseLevel(self.g4_verbose_level)

        # Cannot be initialized two times (ftm)
        if self.initialized:
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
        # self.g4_PhysList = gam.create_phys_list(self.physics_info)
        self.g4_RunManager.SetUserInitialization(self.physics_manager.g4_physic_list)
        # gam.set_cuts(self.physics_info, self.g4_PhysList)

        # sources
        log.info('Simulation: initialize Source')
        self.source_manager.run_timing_intervals = self.run_timing_intervals

        # visualisation
        self._initialize_visualisation()

        # action
        log.info('Simulation: initialize Actions')
        self.action_manager = gam.ActionManager(self.source_manager)
        self.g4_RunManager.SetUserInitialization(self.action_manager)

        # Initialization
        log.info('Simulation: initialize G4RunManager')
        self.g4_RunManager.Initialize()
        self.initialized = True

        # Actors initialization
        log.info('Simulation: initialize Actors')
        self.actor_manager.initialize(self.action_manager)

        # Check overlaps
        log.info('Simulation: check volumes overlap')
        self.check_geometry_overlaps(verbose=False)

        # Register sensitive detector.
        # if G4 was compiled with MT (regardless it is used or not)
        # ConstructSDandField (in VolumeManager) will be automatically called
        if not g4.GamInfo.get_G4MULTITHREADED():
            gam.warning('DEBUG Register sensitive detector in no MT mode')
            self.simulation.actor_manager.register_sensitive_detectors()

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.initialized:
            gam.fatal(f'Please, use g4_apply_command *after* simulation.initialize()')
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    def start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        if not self.initialized:
            gam.fatal('Use "initialize" before "start"')
        log.info('-' * 80 + '\nSimulation: START')

        # visualisation should be initialized *after* other initializations
        self._initialize_visualisation()

        # actor: start simulation (only main thread)
        try:
            self.actor_manager.start_simulation()
        except:
            print('ICICIXIXI')
            gam.fatal("dss")

        # go !
        start = time.time()
        self.source_manager.start()
        end = time.time()

        # actor: stop simulation
        self.actor_manager.stop_simulation()

        # this is the end
        log.info(f'Simulation: STOP. Run: {len(self.run_timing_intervals)}. '
                 # f'Events: {self.source_manager.total_events_count}. '
                 f'Time: {end - start:0.1f} seconds.\n'
                 + f'-' * 80)

    def set_g4_MT(self, b):
        self.set_g4_multi_thread(b)

    def set_g4_multi_thread(self, b, nb=2):
        mt = g4.GamInfo.get_G4MULTITHREADED()
        if b and not mt:
            gam.fatal('Cannot use multi-thread, gam_g4 was not compiled with Geant4 MT')
        self.g4_multi_thread_flag = b
        self.number_of_threads = nb

    def set_g4_random_engine(self, engine_name, seed='auto'):
        # FIXME add more random engine later
        if engine_name != 'MersenneTwister':
            s = f'Cannot find the random engine {engine_name}\n'
            s += f'Use: MersenneTwister'
            gam.fatal(s)
        self.g4_HepRandomEngine = g4.MTwistEngine()
        g4.G4Random.setTheEngine(self.g4_HepRandomEngine)
        self.seed = seed
        if seed == 'auto':
            self.seed = random.randrange(sys.maxsize)
        g4.G4Random.setTheSeeds(self.seed, 0)

    def set_g4_verbose(self, b=True, level=1):
        self.g4_verbose = b
        self.g4_verbose_level = level
        # For a unknow reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        if not b:
            ui = gam.UIsessionSilent()
            self.set_g4_ui_output(ui)
        else:
            self.set_g4_ui_output(None)

    def set_g4_ui_output(self, ui_session):
        # we must kept a ref to ui_session
        self.ui_session = ui_session
        # we must kept a ref to ui_manager
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.SetCoutDestination(ui_session)

    def set_g4_visualisation_flag(self, b):
        if self.initialized:
            gam.fatal(f'Cannot change visualisation *after* the initialisation')
        self.g4_visualisation_options.g4_visualisation_flag = b

    def _add_element(self, elements, element_type, element_name):
        # FIXME will be removed
        if element_name in elements:
            s = f"Error, cannot add '{element_name}' because an element already exists" \
                f' in: {elements}.'
            gam.fatal(s)
        elements[element_name] = Box()
        e = elements[element_name]
        e.name = element_name
        e.type = element_type
        return e

    def get_volume_info(self, name):
        v = self.volume_manager.get_volume(name)
        return v.user_info

    def get_source_info(self, name):
        s = self.source_manager.get_source(name)
        return s.user_info

    def get_actor_info(self, name):
        s = self.actor_manager.get_actor(name)
        return s.user_info

    def get_actor(self, name):
        return self.actor_manager.get_actor(name)

    def add_volume(self, solid_type, name):
        return self.volume_manager.add_volume(solid_type, name)

    def add_source(self, source_type, name):
        return self.source_manager.add_source(source_type, name)

    def add_actor(self, actor_type, name):
        return self.actor_manager.add_actor(actor_type, name)

    def add_material_database(self, filename, name=None):
        self.volume_manager.add_material_database(filename, name)

    def _initialize_visualisation(self):
        self.source_manager.g4_visualisation_options = self.g4_visualisation_options
        if not self.g4_visualisation_options.g4_visualisation_flag:
            return
        log.info('Simulation: initialize visualisation')

    def check_geometry_overlaps(self, verbose=True):
        if not self.initialized:
            gam.fatal(f'Cannot check overlap: the simulation must be initialized before')
        # FIXME: later, allow to bypass this check ?
        # FIXME: How to manage the verbosity ?
        b = self.g4_verbose
        self.set_g4_verbose(verbose)
        self.volume_manager.check_overlaps()
        self.set_g4_verbose(b)
