from opengate import log
import time
import random
import sys
import os
from .ExceptionHandler import *
from multiprocessing import (
    Process,
    set_start_method,
    Manager,
    active_children,
    cpu_count,
)
from opengate_core import G4RunManagerFactory
from .Decorators import requires_fatal
from .helpers import fatal, warning

import weakref


class SimulationEngine(gate.EngineBase):
    """
    Main class to execute a Simulation (optionally in a separate subProcess)
    """

    def __init__(self, simulation, start_new_process=False):
        self.simulation = simulation
        gate.EngineBase.__init__(self, self)

        # current state of the engine
        self.run_timing_intervals = None
        self.state = "before"  # before | started | after
        self.is_initialized = False

        # do we create a subprocess or not ?
        self.start_new_process = start_new_process

        # LATER : option to wait the end of completion or not

        # store the simulation object
        self.verbose_close = simulation.verbose_close
        self.verbose_destructor = simulation.verbose_destructor
        self.verbose_getstate = simulation.verbose_getstate

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
        self.g4_StateManager = g4.G4StateManager.GetStateManager()

        # life cycle management
        self.run_manager_finalizer = None
        self._is_closed = False

        # exception handler
        self.g4_exception_handler = None

        # user fct to call after initialization
        self.user_fct_after_init = simulation.user_fct_after_init
        # a list to store short log messages
        # produced by hook function such as user_fct_after_init
        self.hook_log = []

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting SimulationEngine")

    def close_engines(self):
        if self.volume_engine:
            self.volume_engine.close()
        if self.physics_engine:
            self.physics_engine.close()
        if self.source_engine:
            self.source_engine.close()
        if self.action_engine:
            self.action_engine.close()
        if self.actor_engine:
            self.actor_engine.close()

    def release_engines(self):
        self.volume_engine = None
        self.physics_engine = None
        self.source_engine = None
        self.action_engine = None
        self.actor_engine = None

    def release_g4_references(self):
        self.g4_ui = None
        self.g4_HepRandomEngine = None
        self.g4_StateManager = None
        self.g4_exception_handler = None

    def notify_managers(self):
        self.simulation.physics_manager._simulation_engine_closing()
        self.simulation.volume_manager._simulation_engine_closing()

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing SimulationEngine is_closed = {self._is_closed}")
        if self._is_closed is False:
            self.close_engines()
            self.release_engines()
            self.release_g4_references()
            self.notify_managers()
            if self.g4_RunManager:
                self.g4_RunManager.SetVerboseLevel(0)
            self._is_closed = True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    # define thus as property so the condition can be changed
    # without need to refactor the code
    @property
    def run_multithreaded(self):
        return (
            self.simulation.user_info.number_of_threads > 1
            or self.simulation.user_info.force_multithread_mode
        )

    def start(self):
        if self.start_new_process and not os.name == "nt":
            """
            set_start_method only work with linux and osx, not with windows
            https://superfastpython.com/multiprocessing-spawn-runtimeerror

            Alternative: put the
            if __name__ == '__main__':
            at the beginning of the script
            https://britishgeologicalsurvey.github.io/science/python-forking-vs-spawn/

            (the "force" option is needed for notebooks)

            for windows, fork does not work and spawn produces an error, so for the moment we remove the process part
            to be able to run process, we will need to start the example in __main__
            https://stackoverflow.com/questions/18204782/runtimeerror-on-windows-trying-python-multiprocessing

            """
            set_start_method("fork", force=True)
            # set_start_method("spawn")
            q = Manager().Queue()
            p = Process(target=self.init_and_start, args=(q,))
            p.start()

            self.state = "started"
            p.join()  # (timeout=10)  # timeout might be needed
            self.state = "after"
            output = q.get()
        else:
            output = self.init_and_start(None)

        # put back the simulation object to all actors
        for actor in output.actors.values():
            actor.simulation = self.simulation
        output.simulation = self.simulation

        # start visualization if vrml or gdml
        if (
            self.simulation.user_info.visu is True
            and self.simulation.user_info.visu_type == "vrml"
        ):
            self.vrml_visualization()
        elif (
            self.simulation.user_info.visu is True
            and self.simulation.user_info.visu_type == "gdml"
        ):
            self.gdml_visualization()

        # return the output of the simulation
        return output

    def init_and_start(self, queue):
        self.state = "started"

        # initialization
        self.initialize_visualisation()
        self.initialize()

        # things to do after init and before run
        self.apply_all_g4_commands()
        if self.user_fct_after_init:
            log.info("Simulation: initialize user fct")
            self.user_fct_after_init(self)

        # go
        self._start()

        # prepare the output
        output = gate.SimulationOutput()
        output.store_actors(self)
        output.store_sources(self)
        output.store_hook_log(self)
        output.current_random_seed = self.current_random_seed
        if queue is not None:
            queue.put(output)
            return None
        else:
            return output

    def initialize(self):
        """
        Build the main geant4 objects and initialize them.
        """

        # create engines
        self.volume_engine = gate.VolumeEngine(self)
        self.physics_engine = gate.PhysicsEngine(self)
        self.source_engine = gate.SourceEngine(self)
        self.action_engine = gate.ActionEngine(self)
        self.actor_engine = gate.ActorEngine(self)

        # shorter code
        ui = self.simulation.user_info

        # g4 verbose
        self.initialize_g4_verbose()

        # init random engine (before the MTRunManager creation)
        self.initialize_random_engine()

        # create the run manager (assigned to self.g4_RunManager)
        self.create_run_manager()

        # create the handler for the exception
        self.g4_exception_handler = ExceptionHandler()

        # check run timing
        self.run_timing_intervals = self.simulation.run_timing_intervals.copy()
        gate.assert_run_timing(self.run_timing_intervals)

        # Geometry initialization
        log.info("Simulation: initialize Geometry")
        self.volume_engine.verbose_destructor = self.verbose_destructor

        # Set the userDetector pointer of the Geant4 run manager
        # to VolumeEngine object defined here in open-gate
        self.g4_RunManager.SetUserInitialization(self.volume_engine)
        # Important: The volumes are constructed
        # when the G4RunManager calls the Construct method of the VolumeEngine,
        # which happens in the InitializeGeometry method of the
        # G4RunManager (Geant4 code)

        # Physics initialization
        log.info("Simulation: initialize Physics")
        self.physics_engine.initialize_before_runmanager()
        self.g4_RunManager.SetUserInitialization(self.physics_engine.g4_physics_list)

        # check if some actors need UserEventInformation
        self.enable_user_event_information(
            self.simulation.actor_manager.user_info_actors.values()
        )

        # sources
        log.info("Simulation: initialize Source")
        self.source_engine.initialize(self.simulation.run_timing_intervals)

        # action
        self.g4_RunManager.SetUserInitialization(self.action_engine)

        # Actors initialization (before the RunManager Initialize)
        log.info("Simulation: initialize Actors")
        self.actor_engine.create_actors()  # calls the actors' constructors
        self.source_engine.initialize_actors(self.actor_engine.actors)

        # Visu
        if self.simulation.user_info.visu:
            log.info("Simulation: initialize Visualization")
            self.vi_manager = g4.G4VisExecutive("all")
            self.vi_manager.Initialize()

        # Note: In serial mode, SetUserInitialization() would only be needed
        # for geometry and physics, but in MT mode the fake run for worker
        # initialization needs a particle source.
        log.info("Simulation: initialize G4RunManager")
        if self.run_multithreaded is True:
            self.g4_RunManager.InitializeWithoutFakeRun()
        else:
            self.g4_RunManager.Initialize()

        self.physics_engine.initialize_after_runmanager()
        self.g4_RunManager.PhysicsHasBeenModified()

        # G4's MT RunManager needs an empty run to initialize workers
        if self.run_multithreaded is True:
            self.g4_RunManager.FakeBeamOn()

        # Actions initialization
        self.actor_engine.action_engine = self.action_engine
        self.actor_engine.initialize()

        self.is_initialized = True

        # Check overlaps
        if ui.check_volumes_overlap:
            log.info("Simulation: check volumes overlap")
            self.check_volumes_overlap(verbose=False)
        else:
            log.info("Simulation: (no volumes overlap checking)")

        # Register sensitive detector.
        # if G4 was compiled with MT (regardless if it is used or not)
        # ConstructSDandField (in VolumeManager) will be automatically called
        if not g4.GateInfo.get_G4MULTITHREADED():
            gate.fatal("DEBUG Register sensitive detector in no MT mode")
            # todo : self.actor_engine.register_sensitive_detectors()

        # vrml initialization
        self.initialize_visualisation()

    def create_run_manager(self):
        """Get the correct RunManager according to the requested threads
        and make some basic settings.

        """
        if self.g4_RunManager:
            fatal("A G4RunManager as already been created.")

        ui = self.simulation.user_info

        if self.run_multithreaded is True:
            # GetOptions() returns a set which should contain 'MT'
            # if Geant4 was compiled with G4MULTITHREADED
            if "MT" not in G4RunManagerFactory.GetOptions():
                fatal(
                    "Geant4 does not support multithreading. Probably it was compiled without G4MULTITHREADED flag."
                )

            log.info(
                f"Simulation: create MTRunManager with {ui.number_of_threads} threads"
            )
            self.g4_RunManager = g4.WrappedG4MTRunManager()
            self.g4_RunManager.SetNumberOfThreads(ui.number_of_threads)
        else:
            log.info("Simulation: create RunManager (single thread)")
            self.g4_RunManager = g4.WrappedG4RunManager()

        if self.g4_RunManager is None:
            fatal("Unable to create RunManager")

        self.g4_RunManager.SetVerboseLevel(ui.g4_verbose_level)
        # this creates a finalizer for the run manager which assures that
        # the close() method is called before the run manager is garbage collected,
        # i.e. G4RunManager destructor is called
        self.run_manager_finalizer = weakref.finalize(self.g4_RunManager, self.close)

    def apply_all_g4_commands(self):
        n = len(self.simulation.g4_commands)
        if n > 0:
            log.info(f"Simulation: apply {n} G4 commands")
        for command in self.simulation.g4_commands:
            self.apply_g4_command(command)

    def gdml_visualization(self):
        try:
            import pyg4ometry
        except Exception as exception:
            gate.warning(exception)
            gate.warning(
                "The module pyg4ometry is maybe not installed or is not working. Try: \n"
                "pip install pyg4ometry"
            )
            return
        r = pyg4ometry.gdml.Reader(self.simulation.user_info.visu_filename)
        l = r.getRegistry().getWorldVolume()
        v = pyg4ometry.visualisation.VtkViewerColouredMaterial()
        v.addLogicalVolume(l)
        v.view()

    def vrml_visualization(self):
        try:
            import pyvista
        except Exception as exception:
            gate.warning(exception)
            gate.warning(
                "The module pyvista is maybe not installed or is not working to be able to visualize vrml files. Try:\n"
                "pip install pyvista"
            )
            return
        pl = pyvista.Plotter()
        pl.import_vrml(self.simulation.user_info.visu_filename)
        pl.add_axes(line_width=5)
        pl.show()

    def apply_g4_command(self, command):
        if self.g4_ui is None:
            self.g4_ui = g4.G4UImanager.GetUIpointer()
        log.info(f"Simulation: Apply G4 command '{command}'")
        self.g4_ui.ApplyCommand(command)

    def _start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        s = ""
        if self.start_new_process:
            s = "(in a new process)"
        log.info("-" * 80 + f"\nSimulation: START {s}")

        # visualisation should be initialized *after* other initializations ?
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

    def initialize_visualisation(self):
        ui = self.simulation.user_info

        # Check when GDML is activated, if G4 was compiled with GDML
        if ui.visu is True and ui.visu_type == "gdml":
            gi = g4.GateInfo
            if not gi.get_G4GDML():
                warning(
                    "Visualization with GDML not available in Geant4. Check G4 compilation."
                )
        # vrml initialization
        if (
            ui.visu is True
            and (ui.visu_type == "vrml_file_only" or ui.visu_type == "vrml")
            and ui.visu_filename
        ):
            os.environ["G4VRMLFILE_FILE_NAME"] = ui.visu_filename

        # gdml initialization
        if (
            ui.visu == True
            and (ui.visu_type == "gdml_file_only" or ui.visu_type == "gdml")
            and ui.visu_filename
        ):
            if os.path.isfile(ui.visu_filename):
                os.remove(ui.visu_filename)

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

        # if windows, the long are 4 bytes instead of 8 bytes for python and unix system
        if os.name == "nt":
            self.current_random_seed = int(
                self.current_random_seed % ((pow(2, 32) - 1) / 2)
            )

        # set the seed
        g4.G4Random.setTheSeed(self.current_random_seed, 0)

    def initialize_g4_verbose(self):
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
        if self.g4_ui is None:
            fatal("Unable to obtain a UIpointer")
        self.g4_ui.SetCoutDestination(ui)

    # FIXME: rename to avoid conflict with function in helpers.
    # should be more specific, like fatal_multiple_execution
    def fatal(self, err=""):
        s = (
            f"Cannot run a new simulation in this process: only one execution is possible.\n"
            f"Use the option start_new_process=True in gate.SimulationEngine. {err}"
        )
        gate.fatal(s)

    def check_volumes_overlap(self, verbose=True):
        # we need to 'cheat' the verbosity before doing the check
        ui = self.simulation.user_info
        b = ui.g4_verbose
        ui.g4_verbose = True
        self.initialize_g4_verbose()

        # check
        self.volume_engine.check_overlaps(verbose)

        # put back verbosity
        ui.g4_verbose = b
        self.initialize_g4_verbose()

    @property
    @requires_fatal("g4_StateManager")
    def g4_state(self):
        return self.g4_StateManager.GetCurrentState()

    @g4_state.setter
    @requires_fatal("g4_StateManager")
    def g4_state(self, g4_application_state):
        self.g4_StateManager.SetNewState(g4_application_state)

    # @property
    # def initializedAtLeastOnce(self):
    #     if self.g4_RunManager is None:
    #         return False
    #     else:
    #         return self.g4_RunManager.GetInitializedAtLeastOnce()

    # @initializedAtLeastOnce.setter
    # def initializedAtLeastOnce(self, tf):
    #     if self.g4_RunManager is None:
    #         gate.fatal(
    #             "Cannot set 'initializedAtLeastOnce' variable. No RunManager available."
    #         )
    #     self.g4_RunManager.SetInitializedAtLeastOnce(tf)

    def enable_user_event_information(self, actors):
        self.user_event_information_flag = False
        for ac in actors:
            if "attributes" in ac.__dict__:
                if "ParentParticleName" in ac.attributes:
                    self.user_event_information_flag = True
                    return
