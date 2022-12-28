from opengate import log
import time
import random
import sys
from .ExceptionHandler import *
from multiprocessing import Process, set_start_method, Queue
import os


class SimulationEngine:
    """
    Main class to execute a Simulation (optionally in a separate Process)
    """

    def __init__(self):
        self.state = "before"  # before | started | after
        """
        FIXME
        apply_g4_command <--- store a list of commands to apply after init
        """

        # UI
        self.ui_session = None
        self.g4_ui = None
        # random engine
        self.g4_HepRandomEngine = None
        self.current_random_seed = None
        # Main Run Manager
        self.g4_RunManager = None
        # exception handler
        self.g4_exception_handler = None

    def __del__(self):
        print("del SimulationEngine")
        # set verbose to zero before destructor to avoid the final message
        # if getattr(self, "g4_RunManager", False):
        #    self.g4_RunManager.SetVerboseLevel(0)
        pass

    def start(self, simulation):
        print("SimulationEngine initialize : start a Process", os.getpid())
        # set start method only work on linux and osx, not windows
        # https://superfastpython.com/multiprocessing-spawn-runtimeerror/
        # Alternative: put the
        # if __name__ == '__main__':
        # at the beginning of the script
        set_start_method("fork")
        q = Queue()
        p = Process(target=self.init_and_start, args=(simulation, q))
        p.start()
        self.state = "started"
        p.join()
        self.state = "after"
        return q.get()

    def init_and_start(self, simulation, queue):
        self.state = "started"
        print("module name:", __name__)
        print("parent process:", os.getppid())
        print("process id:", os.getpid())
        print("_start", self)
        print("_start", simulation)
        print("_start", queue)
        self._initialize(simulation)
        print("after initialize")
        self._start(simulation)
        print("after start")
        queue.put(self)

    def _initialize(self, simulation):
        """
        Build the main geant4 objects and initialize them.
        """
        # shorter code
        ui = simulation.user_info

        # g4 verbose
        self.initialize_g4_verbose(simulation)

        # check multithreading
        mt = g4.GateInfo.get_G4MULTITHREADED()
        if ui.number_of_threads > 1 and not mt:
            gate.fatal(
                "Cannot use multi-thread, opengate_core was not compiled with Geant4 MT"
            )

        # check if RunManager already exists (it should not)
        # FIXME check if RM does not already exist
        """if ui.number_of_threads > 1 or ui.force_multithread_mode:
            rm = g4.G4MTRunManager.GetRunManager()
        else:
            rm = g4.G4RunManager.GetRunManager()

        if rm:
            s = f"Cannot create a Simulation, the G4RunManager already exist."
            gate.fatal(s)"""

        # init random engine (before the MTRunManager creation)
        self.initialize_random_engine(simulation)

        # create the RunManager
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            log.info(
                f"Simulation: create MTRunManager with {ui.number_of_threads} threads"
            )
            rm = g4.G4RunManagerFactory.CreateMTRunManager(ui.number_of_threads)
            rm.SetNumberOfThreads(ui.number_of_threads)
        else:
            log.info("Simulation: create RunManager")
            rm = g4.G4RunManagerFactory.CreateRunManager()

        self.g4_RunManager = rm
        self.g4_RunManager.SetVerboseLevel(ui.g4_verbose_level)

        # create the handler for the exception
        self.g4_exception_handler = ExceptionHandler()

        # check run timing
        gate.assert_run_timing(simulation.run_timing_intervals)

        """
        - 1) create DetectorConstruction from VolumeManager
        - 2) initialize / create physics G4 objects from PhysicsManager
            g4_physic_list factory g4_decay g4_radioactive_decay
            g4_cuts_by_regions (G4ProductionCuts)
        - 3) initialize / create source from Source Manager
            g4_master_source_manager g4_thread_source_managers
            particle_table (g4 !)
            (will need actors in initialize_actors)
        - 4) ActionManager with source manager
        - 5) create_actors with ActionManager + source_manager.initialize_actors
        - 6) g4_RunManager.Initialize()
        - 7) initialize_cuts
        - 8) actor_manager.initialize()
        - 9) self.check_volumes_overlap
        - 10) register_sensitive_detectors

        Solution1 : all g4 object as members
        Solution2 : one G4 "engine" class for all managers ? <-- start by that

        """

        # geometry
        log.info("Simulation: initialize Geometry")
        self.volume_engine = gate.VolumeManagerEngine(simulation)
        self.g4_RunManager.SetUserInitialization(self.volume_engine)

        # phys
        log.info("Simulation: initialize Physics")
        self.physics_engine = gate.PhysicsManagerEngine(simulation.physics_manager)
        self.g4_RunManager.SetUserInitialization(self.physics_engine.g4_physic_list)

        # sources
        log.info("Simulation: initialize Source")
        self.source_manager.run_timing_intervals = self.run_timing_intervals
        self.source_manager.initialize(self.run_timing_intervals)

        # action
        log.info("Simulation: initialize Actions")
        self.action_manager = gate.ActionManager(self.source_manager)
        self.g4_RunManager.SetUserInitialization(self.action_manager)

        # Actors initialization (before the RunManager Initialize)
        self.actor_manager.create_actors(self.action_manager)
        self.source_manager.initialize_actors(self.actor_manager.actors)

        # Initialization
        log.info("Simulation: initialize G4RunManager")
        self.g4_RunManager.Initialize()
        self.is_initialized = True

        # Physics cuts initialization
        log.info("Simulation: initialize Physics cuts")
        tree = self.volume_engine.volumes_tree
        self.physics_engine.initialize_cuts(tree)

        # Actors initialization
        log.info("Simulation: initialize Actors")
        self.actor_manager.initialize()

        # Check overlaps
        if ui.check_volumes_overlap:
            log.info("Simulation: check volumes overlap")
            self.check_volumes_overlap(verbose=False)

        # Register sensitive detector.
        # if G4 was compiled with MT (regardless it is used or not)
        # ConstructSDandField (in VolumeManager) will be automatically called
        if not g4.GateInfo.get_G4MULTITHREADED():
            gate.warning("DEBUG Register sensitive detector in no MT mode")
            self.actor_manager.register_sensitive_detectors()

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.is_initialized:
            gate.fatal(f"Please, use g4_apply_command *after* simulation.initialize()")
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    def start_2(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        if not self.is_initialized:
            gate.fatal('Use "initialize" before "start"')
        log.info("-" * 80 + "\nSimulation: START")

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
        log.info(
            f"Simulation: STOP. Run: {len(self.run_timing_intervals)}. "
            # f'Events: {self.source_manager.total_events_count}. '
            f"Time: {end - start:0.1f} seconds.\n"
            + f"-" * 80
        )

    def initialize_random_engine(self, simulation):
        engine_name = simulation.user_info.random_engine
        self.g4_HepRandomEngine = None
        if engine_name == "MixMaxRng":
            self.g4_HepRandomEngine = g4.MixMaxRng()
        if engine_name == "MersenneTwister":
            self.g4_HepRandomEngine = g4.MTwistEngine()
        if not self.g4_HepRandomEngine:
            s = f"Cannot find the random engine {engine_name}\n"
            s += f"Use: MersenneTwister or MixMaxRng"
            gate.fatal(s)

        # set the random engine
        g4.G4Random.setTheEngine(self.g4_HepRandomEngine)
        if simulation.user_info.random_seed == "auto":
            self.current_random_seed = random.randrange(sys.maxsize)
        else:
            self.current_random_seed = simulation.user_info.random_seed

        # set the seed
        g4.G4Random.setTheSeed(self.current_random_seed, 0)

    def initialize_g4_verbose(self, simulation):
        # For an unknown reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        ui = None
        if not simulation.user_info.g4_verbose:
            # no Geant4 output
            ui = gate.UIsessionSilent()
        else:
            # Geant4 output with color
            ui = gate.UIsessionVerbose()
        # it is also possible to set ui=None for 'default' output
        # we must keep a ref to ui_session
        self.ui_session = ui
        # we must keep a ref to ui_manager
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.SetCoutDestination(ui)

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

    def check_volumes_overlap(self, verbose=True):
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
        self.initialize_g4_verbose()
