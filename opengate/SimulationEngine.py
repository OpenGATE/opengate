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

    def __init__(self, simulation):
        self.state = "before"  # before | started | after
        """
        FIXME
        apply_g4_command <--- store a list of commands to apply after init
        """

        # store the simulation object
        self.simulation = simulation

        # UI
        self.ui_session = None
        self.g4_ui = None

        # all engines
        self.volume_engine = None
        self.physics_engine = None
        self.source_engine = None
        self.action_engine = None
        self.actor_engine = None

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

    def start(self):
        print("SimulationEngine initialize : start a Process", os.getpid())
        # set start method only work on linux and osx, not windows
        # https://superfastpython.com/multiprocessing-spawn-runtimeerror/
        # Alternative: put the
        # if __name__ == '__main__':
        # at the beginning of the script
        set_start_method("fork")
        q = Queue()
        p = Process(target=self.init_and_start, args=(q,))
        p.start()
        self.state = "started"
        p.join()
        print("after join")
        self.state = "after"
        return q.get()

    def init_and_start(self, queue):
        self.state = "started"
        print("module name:", __name__)
        print("parent process:", os.getppid())
        print("process id:", os.getpid())
        print("_start", self)
        print("_start", self.simulation)
        print("_start", queue)
        self._initialize()
        print("after initialize")
        self._start()
        print("after start")
        # queue.put() # prepare an output !
        # queue.put(True)
        s = self.actor_engine.actors["Stats"]
        print(f"s {s}")
        # queue.put(s, block=False)
        # queue.put(self.actor_engine.actors)
        print("end init and start")

    def _initialize(self):
        """
        Build the main geant4 objects and initialize them.
        """
        # shorter code
        ui = self.simulation.user_info

        # g4 verbose
        self.initialize_g4_verbose()

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
        self.initialize_random_engine()

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
        self.run_timing_intervals = self.simulation.run_timing_intervals.copy()
        gate.assert_run_timing(self.run_timing_intervals)

        # geometry
        log.info("Simulation: initialize Geometry")
        self.volume_engine = gate.VolumeEngine(self.simulation, self)
        self.g4_RunManager.SetUserInitialization(self.volume_engine)

        # phys
        log.info("Simulation: initialize Physics")
        self.physics_engine = gate.PhysicsEngine(self.simulation.physics_manager)
        self.physics_engine.initialize()
        self.g4_RunManager.SetUserInitialization(self.physics_engine.g4_physic_list)

        # sources
        log.info("Simulation: initialize Source")
        self.source_engine = gate.SourceEngine(self.simulation.source_manager)
        self.source_engine.initialize(self.simulation.run_timing_intervals)

        # action
        log.info("Simulation: initialize Actions")
        self.action_engine = gate.ActionEngine(self.source_engine)
        self.g4_RunManager.SetUserInitialization(self.action_engine)

        # Actors initialization (before the RunManager Initialize)
        self.actor_engine = gate.ActorEngine(
            self.simulation.actor_manager, self.volume_engine
        )
        self.actor_engine.create_actors(self.action_engine)
        self.source_engine.initialize_actors(self.actor_engine.actors)

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
        self.actor_engine.initialize()

        # Check overlaps
        if ui.check_volumes_overlap:
            gate.warning(f"check_volumes_overlap NOT IMPLEMENTED YET")
            # log.info("Simulation: check volumes overlap")
            # self.check_volumes_overlap(verbose=False)

        # Register sensitive detector.
        # if G4 was compiled with MT (regardless it is used or not)
        # ConstructSDandField (in VolumeManager) will be automatically called
        if not g4.GateInfo.get_G4MULTITHREADED():
            gate.warning("DEBUG Register sensitive detector in no MT mode")
            self.actor_engine.register_sensitive_detectors()

    def apply_g4_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.is_initialized:
            gate.fatal(f"Please, use g4_apply_command *after* simulation.initialize()")
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    def _start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        log.info("-" * 80 + "\nSimulation: START")

        # FIXME check run_timing_intervals

        # visualisation should be initialized *after* other initializations
        # FIXME self._initialize_visualisation()

        # actor: start simulation (only the master thread)
        self.actor_engine.start_simulation()

        # go !
        start = time.time()
        self.source_engine.start()
        end = time.time()

        # actor: stop simulation (only the master thread)
        self.actor_engine.stop_simulation()

        # this is the end
        log.info(
            f"Simulation: STOP. Run: {len(self.run_timing_intervals)}. "
            # f'Events: {self.source_manager.total_events_count}. '
            f"Time: {end - start:0.1f} seconds.\n"
            + f"-" * 80
        )

    def initialize_random_engine(self):
        engine_name = self.simulation.user_info.random_engine
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
        if self.simulation.user_info.random_seed == "auto":
            self.current_random_seed = random.randrange(sys.maxsize)
        else:
            self.current_random_seed = self.simulation.user_info.random_seed

        # set the seed
        g4.G4Random.setTheSeed(self.current_random_seed, 0)

    def initialize_g4_verbose(self):
        # For an unknown reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        if not self.simulation.user_info.g4_verbose:
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

    def get_source(self, name):
        return self.source_engine.get_source(name)

    def get_source_MT(self, name, thread):
        return self.source_engine.get_source_MT(name, thread)

    def get_actor(self, name):
        if not self.is_initialized:
            gate.fatal(f"Cannot get an actor before initialization")
        return self.actor_engine.get_actor(name)

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
