import time
import random
import sys
import os
from multiprocessing import Process, set_start_method, Manager
import queue
import weakref
from box import Box

import opengate_core as g4

from .exception import fatal, warning
from .decorators import requires_fatal, requires_warning
from .logger import log
from .runtiming import assert_run_timing
from .uisessions import UIsessionSilent, UIsessionVerbose
from .exception import ExceptionHandler
from .element import new_element
from .physics import (
    UserLimitsPhysics,
    translate_particle_name_gate2G4,
    cut_particle_names,
)
from .definitions import __world_name__
from .geometry.utility import build_tree


class EngineBase:
    """
    Base class for all engines (SimulationEngine, VolumeEngine, etc.)
    """

    def __init__(self, simulation_engine):
        self.simulation_engine = simulation_engine
        # debug verbose
        self.verbose_destructor = simulation_engine.simulation.verbose_destructor
        self.verbose_getstate = simulation_engine.simulation.verbose_getstate
        self.verbose_close = simulation_engine.simulation.verbose_close


class SourceEngine(EngineBase):
    """
    Source Engine manages the G4 objects of sources at runtime
    """

    # G4RunManager::BeamOn takes an int as input. The max cpp int value is currently 2147483647
    # Python manages int differently (no limit), so we need to set the max value here.
    max_int = 2147483647

    def __init__(self, simulation_engine):
        EngineBase.__init__(self, simulation_engine)

        # Keep a pointer to the current simulation
        # self.source_manager = source_manager
        self.simulation_engine = simulation_engine

        # List of run time intervals
        self.run_timing_intervals = None
        self.current_run_interval = None

        # List of sources (GateSource), for all threads
        self.sources = []

        # The source manager will be constructed at build (during ActionManager)
        # Its task is to call GeneratePrimaries and loop over the sources
        # For MT, the master_source_manager is the MasterThread
        # The g4_thread_source_managers list all master sources for all threads
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = []

        # internal variables
        self.g4_particle_table = None

        # Options dict for cpp SourceManager
        # will be set in create_g4_source_manager
        self.source_manager_options = Box()

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting SourceEngine")

    def close(self):
        if self.verbose_close:
            warning(f"Closing SourceEngine")
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = None
        self.g4_particle_table = None
        # a source object contains a reference to a G4 source
        self.sources = None

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        assert_run_timing(self.run_timing_intervals)
        if len(self.simulation_engine.simulation.source_manager.user_info_sources) == 0:
            warning(f"No source: no particle will be generated")

    def initialize_actors(self, actors):
        """
        Parameters
        ----------
        actors : dict
            The dictionary ActorEngine.actors which contains key-value pairs
            "actor_name" : "Actor object"
        """
        self.g4_master_source_manager.SetActors(list(actors.values()))

    def create_master_source_manager(self):
        # create particles table # FIXME in physics ??
        # NK: I don't think this is the correct approach
        # The particles are constructed through the RunManager when the
        # physics list is initialized, namely in G4RunManagerKernel::SetupPhysics()
        # self.g4_particle_table = g4.G4ParticleTable.GetParticleTable()
        # self.g4_particle_table.CreateAllParticles()  # Warning: this is a hard-coded list!
        # create the master source for the masterThread
        self.g4_master_source_manager = self.create_g4_source_manager(append=False)
        return self.g4_master_source_manager

    def create_g4_source_manager(self, append=True):
        """
        This is called by all threads
        This object is needed here, because it can only be
        created after physics initialization
        """
        ms = g4.GateSourceManager()
        # create all sources for this source manager (for all threads)
        source_manager = self.simulation_engine.simulation.source_manager
        for vu in source_manager.user_info_sources.values():
            source = new_element(vu, self.simulation_engine.simulation)
            ms.AddSource(source.g4_source)
            source.initialize(self.run_timing_intervals)
            self.sources.append(source)
        # taking __dict__ allow to consider the class SimulationUserInfo as a dict
        sui = self.simulation_engine.simulation.user_info.__dict__
        # warning: copy the simple elements from this dict (containing visu or verbose)
        for s in sui:
            if "visu" in s or "verbose_" in s:
                self.source_manager_options[s] = sui[s]
        ms.Initialize(self.run_timing_intervals, self.source_manager_options)
        # set the flag for user event info
        ms.fUserEventInformationFlag = (
            self.simulation_engine.user_event_information_flag
        )
        # keep pointer to avoid deletion
        if append:
            self.g4_thread_source_managers.append(ms)
        return ms

    def start(self):
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # to allow better control on geometry between the different runs
        # (2) : check estimated nb of particle, warning if too large
        # start the master thread (only main thread)
        self.g4_master_source_manager.StartMasterThread()

        # once terminated, packup the sources (if needed)
        for source in self.sources:
            source.prepare_output()


class PhysicsEngine(EngineBase):
    """
    Class that contains all the information and mechanism regarding physics
    to actually run a simulation. It is associated with a simulation engine.

    """

    def __init__(self, simulation_engine):
        EngineBase.__init__(self, simulation_engine)
        # Keep a pointer to the current physics_manager
        self.physics_manager = simulation_engine.simulation.physics_manager

        # keep a pointer to the simulation engine
        # to which this physics engine belongs
        self.simulation_engine = simulation_engine

        for region in self.physics_manager.regions.values():
            region.physics_engine = self

        # main g4 physic list
        self.g4_physics_list = None
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = []
        self.g4_em_parameters = None
        self.g4_parallel_world_physics = []

        self.gate_physics_constructors = []

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting PhysicsEngine")

    def close(self):
        if self.verbose_close:
            warning(f"Closing PhysicsEngine")
        self.close_physics_constructors()
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_physics_list = None
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = None
        self.g4_em_parameters = None
        self.g4_parallel_world_physics = []

    @requires_fatal("simulation_engine")
    @requires_warning("g4_physics_list")
    def close_physics_constructors(self):
        """This method removes PhysicsConstructors defined in python from the physics list.

        It should be called after a simulation run, i.e. when a simulation engine closes,
        because the RunManager will otherwise attempt to delete the PhysicsConstructor
        and cause a segfault.

        """
        current_state = self.simulation_engine.g4_state
        self.simulation_engine.g4_state = g4.G4ApplicationState.G4State_PreInit
        for pc in self.gate_physics_constructors:
            self.g4_physics_list.RemovePhysics(pc)
        self.simulation_engine.g4_state = current_state

    # make this a property so the communication between
    # PhysicsManager and PhysicsEngine can be changed without
    # impacting this class
    @property
    def user_info_physics_manager(self):
        return self.physics_manager.user_info

    def initialize_before_runmanager(self):
        """Initialize methods to be called *before*
        G4RunManager.Initialize() is called.

        """
        self.initialize_physics_list()
        self.initialize_g4_em_parameters()
        self.initialize_user_limits_physics()
        self.initialize_parallel_world_physics()

    def initialize_after_runmanager(self):
        """ """
        # Cuts need to be set *after*
        # G4RunManager.Initialize() is called.
        # Reason: The Initialize() sequence would otherwise override
        # the global cuts with the physics list defaults.
        self.initialize_global_cuts()
        self.initialize_regions()

    def initialize_parallel_world_physics(self):
        for (
            world
        ) in self.physics_manager.simulation.volume_manager.parallel_world_names:
            pwp = g4.G4ParallelWorldPhysics(world, True)
            self.g4_parallel_world_physics.append(pwp)
            self.g4_physics_list.RegisterPhysics(pwp)

    def initialize_physics_list(self):
        """
        Create a Physic List from the Factory
        """
        physics_list_name = self.physics_manager.user_info.physics_list_name
        self.g4_physics_list = (
            self.physics_manager.physics_list_manager.get_physics_list(
                physics_list_name
            )
        )

    def initialize_regions(self):
        for region in self.physics_manager.regions.values():
            region.initialize()

    def initialize_global_cuts(self):
        ui = self.physics_manager.user_info

        # range
        if ui.energy_range_min is not None and ui.energy_range_max is not None:
            warning(f"WARNING ! SetEnergyRange only works in MT mode")
            pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
            pct.SetEnergyRange(ui.energy_range_min, ui.energy_range_max)

        # Set global production cuts
        # If value is set for 'all', this overrides individual values
        if ui.global_production_cuts.all is not None:
            # calls SetCutValue for all relevant particles,
            # i.e. proton, gamma, e+, e-
            for pname in cut_particle_names.values():
                self.g4_physics_list.SetCutValue(ui.global_production_cuts.all, pname)

        else:
            for pname, value in ui.global_production_cuts.items():
                # ignore 'all', as that's already treated above
                if pname == "all":
                    continue
                if value is not None and value not in ("default", "Default"):
                    self.g4_physics_list.SetCutValue(
                        value, translate_particle_name_gate2G4(pname)
                    )

    def initialize_g4_em_parameters(self):
        self.g4_em_parameters = g4.G4EmParameters.Instance()

        self.g4_em_parameters.SetApplyCuts(self.physics_manager.apply_cuts)

        if self.physics_manager.em_parameters.fluo is not None:
            self.g4_em_parameters.SetFluo(self.physics_manager.em_parameters.fluo)
        if self.physics_manager.em_parameters.auger is not None:
            self.g4_em_parameters.SetAuger(self.physics_manager.em_parameters.auger)
        if self.physics_manager.em_parameters.auger_cascade is not None:
            self.g4_em_parameters.SetAugerCascade(
                self.physics_manager.em_parameters.auger_cascade
            )
        if self.physics_manager.em_parameters.pixe is not None:
            self.g4_em_parameters.SetPixe(self.physics_manager.em_parameters.pixe)
        if self.physics_manager.em_parameters.deexcitation_ignore_cut is not None:
            self.g4_em_parameters.SetDeexcitationIgnoreCut(
                self.physics_manager.em_parameters.deexcitation_ignore_cut
            )

        # set the deex switches only if the user has touched them.
        # Let G4 set its defaults otherwise (i.e. of all are None)
        if any(
            [v is not None for v in self.physics_manager.em_switches_world.values()]
        ):
            # check that all switches were set in case at least one has been set
            # either all must be set or none
            if any(
                [v is None for v in self.physics_manager.em_switches_world.values()]
            ):
                fatal(
                    f"Some EM switches for the world region were not set. You must either set all switches or none. The following switches exist: {self.physics_manager.em_switches_world.keys()}"
                )
            self.g4_em_parameters.SetDeexActiveRegion(
                "world",
                self.physics_manager.em_switches_world.deex,
                self.physics_manager.em_switches_world.auger,
                self.physics_manager.em_switches_world.pixe,
            )
        for region in self.physics_manager.regions.values():
            region.initialize_em_switches()

    @requires_fatal("physics_manager")
    def initialize_user_limits_physics(self):
        need_step_limiter = False
        need_user_special_cut = False
        for r in self.physics_manager.regions.values():
            if r.need_step_limiter() is True:
                need_step_limiter = True
            if r.need_user_special_cut() is True:
                need_user_special_cut = True

        if need_step_limiter or need_user_special_cut:
            user_limits_physics = UserLimitsPhysics()
            user_limits_physics.physics_engine = self
            self.g4_physics_list.RegisterPhysics(user_limits_physics)
            self.gate_physics_constructors.append(user_limits_physics)


class ActionEngine(g4.G4VUserActionInitialization, EngineBase):
    """
    Main object to manage all actions during a simulation.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserActionInitialization.__init__(self)
        EngineBase.__init__(self, simulation_engine)

        # The py source engine
        # self.simulation_engine.source_engine = source
        self.simulation_engine = simulation_engine

        # *** G4 references ***
        # List of G4 source managers (one per thread)
        self.g4_PrimaryGenerator = []

        # The main G4 source manager
        self.g4_main_PrimaryGenerator = None

        # Lists of elements to prevent destruction
        self.g4_RunAction = []
        self.g4_EventAction = []
        self.g4_TrackingAction = []

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting ActionEngine")

    def close(self):
        if self.verbose_close:
            warning(f"Closing ActionEngine")
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_PrimaryGenerator = None
        self.g4_main_PrimaryGenerator = None
        self.g4_RunAction = None
        self.g4_EventAction = None
        self.g4_TrackingAction = None

    def BuildForMaster(self):
        # This function is call only in MT mode, for the master thread
        if not self.g4_main_PrimaryGenerator:
            self.g4_main_PrimaryGenerator = (
                self.simulation_engine.source_engine.create_master_source_manager()
            )

    def Build(self):
        # In MT mode this Build function is invoked
        # for each worker thread, so all user action classes
        # are defined thread-locally.

        # If MT is not enabled, need to create the main source
        if not self.g4_main_PrimaryGenerator:
            p = self.simulation_engine.source_engine.create_master_source_manager()
            self.g4_main_PrimaryGenerator = p
        else:
            # else create a source for each thread
            p = self.simulation_engine.source_engine.create_g4_source_manager()

        self.SetUserAction(p)
        self.g4_PrimaryGenerator.append(p)

        # set the actions for Run
        ra = g4.GateRunAction(p)
        self.SetUserAction(ra)
        self.g4_RunAction.append(ra)

        # set the actions for Event
        ea = g4.GateEventAction()
        self.SetUserAction(ea)
        self.g4_EventAction.append(ea)

        # set the actions for Track
        ta = g4.GateTrackingAction()
        ta.fUserEventInformationFlag = (
            self.simulation_engine.user_event_information_flag
        )
        self.SetUserAction(ta)
        self.g4_TrackingAction.append(ta)


class ActorEngine(EngineBase):
    """
    This object manages all actors G4 objects at runtime
    """

    def __init__(self, simulation_engine):
        EngineBase.__init__(self, simulation_engine)
        # self.actor_manager = simulation.actor_manager
        # we use a weakref because it is a circular dependence
        # with custom __del__
        self.simulation_engine_wr = weakref.ref(simulation_engine)
        self.actors = {}

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting ActorEngine")

    def close(self):
        if self.verbose_close:
            warning(f"Closing ActorEngine")
        for actor in self.actors.values():
            actor.close()
        self.actors = None

    def get_actor(self, name):
        if name not in self.actors:
            fatal(
                f"The actor {name} is not in the current "
                f"list of actors: {self.actors}"
            )
        return self.actors[name]

    def create_actors(self):
        for (
            ui
        ) in (
            self.simulation_engine_wr().simulation.actor_manager.user_info_actors.values()
        ):
            actor = new_element(ui, self.simulation_engine_wr().simulation)
            log.debug(f"Actor: initialize [{ui.type_name}] {ui.name}")
            actor.initialize(self.simulation_engine_wr)
            self.actors[ui.name] = actor

            # create filters
            actor.filters_list = []
            for f in actor.user_info.filters:
                e = new_element(f, self.simulation_engine.simulation)
                e.Initialize(f.__dict__)
                actor.filters_list.append(e)
            # this is a copy to cpp ('append' cannot be used because fFilters is a std::vector)
            actor.fFilters = actor.filters_list

    def initialize(self, volume_engine=None):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        # for actor in self.actors.values():
        for actor in sorted_actors:
            log.debug(
                f"Actor: initialize [{actor.user_info.type_name}] {actor.user_info.name}"
            )
            self.register_all_actions(actor)
            # warning : the step actions will be registered by register_sensitive_detectors
            # called by ConstructSDandField

    def register_all_actions(self, actor):
        # Run
        for ra in self.simulation_engine_wr().action_engine.g4_RunAction:
            ra.RegisterActor(actor)
        # Event
        for ea in self.simulation_engine_wr().action_engine.g4_EventAction:
            ea.RegisterActor(actor)
        # Track
        for ta in self.simulation_engine_wr().action_engine.g4_TrackingAction:
            ta.RegisterActor(actor)
        # initialization
        actor.ActorInitialize()

    def register_sensitive_detectors(
        self, world_name, tree, volume_manager, volume_engine
    ):
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)

        for actor in sorted_actors:
            if "SteppingAction" not in actor.fActions:
                continue

            # Step: only enabled if attachTo a given volume.
            # Propagated to all child and sub-child
            # tree = volume_manager.volumes_tree
            mothers = actor.user_info.mother
            if isinstance(mothers, str):
                # make a list with one single element
                mothers = [mothers]
            # add SD for all mothers
            for vol in mothers:
                vol_world = volume_manager.get_volume_world(vol)
                if vol_world != world_name:
                    # this actor is attached to a volume in another world
                    continue
                if vol not in tree:
                    s = (
                        f"Cannot attach the actor {actor.user_info.name} "
                        f"because the volume {vol} does not exists"
                    )
                    fatal(s)
                # Propagate the Geant4 Sensitive Detector to all children
                n = f"{world_name}_{vol}"
                if world_name == __world_name__:
                    n = vol
                lv = volume_engine.g4_volumes[n].g4_logical_volume
                self.register_sensitive_detector_to_child(actor, lv)

    def register_sensitive_detector_to_child(self, actor, lv):
        log.debug(
            f'Actor: "{actor.user_info.name}" '
            f'(attached to "{actor.user_info.mother}") '
            f'set to volume "{lv.GetName()}"'
        )
        actor.RegisterSD(lv)
        n = lv.GetNoDaughters()
        for i in range(n):
            child = lv.GetDaughter(i).GetLogicalVolume()
            self.register_sensitive_detector_to_child(actor, child)

    def start_simulation(self):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        for actor in sorted_actors:
            actor.StartSimulationAction()

    def stop_simulation(self):
        # consider the priority value of the actors
        sorted_actors = sorted(self.actors.values(), key=lambda d: d.user_info.priority)
        for actor in sorted_actors:
            actor.EndSimulationAction()


class ParallelVolumeEngine(g4.G4VUserParallelWorld, EngineBase):
    """
    Volume engine for each parallel world
    """

    def __init__(self, volume_engine, world_name, volumes_user_info):
        g4.G4VUserParallelWorld.__init__(self, world_name)
        EngineBase.__init__(self, volume_engine.simulation_engine)

        # keep input data
        self.volume_engine = volume_engine
        self.world_name = world_name
        self.volumes_user_info = volumes_user_info

        # G4 elements
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

        # needed for ConstructSD
        self.volumes_tree = None

    def release_g4_references(self):
        self.g4_world_phys_vol = None
        self.g4_world_log_vol = None

    def close(self):
        if self.verbose_close:
            warning(f"Closing ParallelVolumeEngine {self.world_name}")
        self.release_g4_references()

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserParallelWorld
        """

        # build the tree of volumes
        self.volumes_tree = build_tree(self.volumes_user_info, self.world_name)

        # build the world Physical and Logical volumes
        self.g4_world_phys_vol = self.GetWorld()
        self.g4_world_log_vol = self.g4_world_phys_vol.GetLogicalVolume()

        # build all other volumes
        self.volume_engine.build_g4_volumes(
            self.volumes_user_info, self.g4_world_log_vol
        )

    def ConstructSD(self):
        tree = self.volumes_tree
        self.volume_engine.simulation_engine.actor_engine.register_sensitive_detectors(
            self.world_name,
            tree,
            self.volume_engine.simulation_engine.simulation.volume_manager,
            self.volume_engine,
        )


class VolumeEngine(g4.G4VUserDetectorConstruction, EngineBase):
    """
    Engine that will create all G4 elements for the hierarchy of volumes.
    Correspond to the G4VUserDetectorConstruction (inherit)
    Also manage the list of parallel worlds.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserDetectorConstruction.__init__(self)
        EngineBase.__init__(self, simulation_engine)
        self.is_constructed = False

        # parallel world info
        self.world_volumes_user_info = {}
        self.parallel_volume_engines = []

        # list of volumes for the main world
        self.volumes_tree = None

        # all G4 volumes are store here
        # (including volumes in parallel worlds)
        self.g4_volumes = {}

        # create the parallel worlds
        self.initialize_parallel_worlds()

    def initialize_parallel_worlds(self):
        # init list of trees
        self.world_volumes_user_info = (
            self.simulation_engine.simulation.volume_manager.separate_parallel_worlds()
        )

        # build G4 parallel volume engine (except for main world)
        for world_name in self.world_volumes_user_info:
            if (
                world_name
                == self.simulation_engine.simulation.volume_manager.world_name
            ):
                continue
            # register a new parallel world
            volumes_user_info = self.world_volumes_user_info[world_name]
            pw = ParallelVolumeEngine(self, world_name, volumes_user_info)
            self.RegisterParallelWorld(pw)
            # store it to avoid destruction
            self.parallel_volume_engines.append(pw)

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting VolumeEngine")

    def close(self):
        if self.verbose_close:
            warning(f"Closing VolumeEngine")
        for pwe in self.parallel_volume_engines:
            pwe.close()
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_volumes = None

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # build the materials
        self.simulation_engine.simulation.volume_manager.material_database.initialize()

        # initial check (not really needed)
        self.simulation_engine.simulation.check_geometry()

        # build the tree of volumes
        volumes_user_info = self.world_volumes_user_info[__world_name__]
        self.volumes_tree = build_tree(volumes_user_info)

        # build all G4 volume objects
        self.build_g4_volumes(volumes_user_info, None)

        # return the (main) world physical volume
        self.is_constructed = True
        return self.g4_volumes[__world_name__].g4_physical_volume

    def check_overlaps(self, verbose):
        for v in self.g4_volumes.values():
            for w in v.g4_physical_volumes:
                try:
                    b = w.CheckOverlaps(1000, 0, verbose, 1)
                    if b:
                        fatal(
                            f'Some volumes overlap the volume "{v}". \n'
                            f"Consider using G4 verbose to know which ones. \n"
                            f"Aborting."
                        )
                except:
                    pass
                    # warning(f'do not check physical volume {w}')

    def find_or_build_material(self, material):
        mat = self.simulation_engine.simulation.volume_manager.material_database.FindOrBuildMaterial(
            material
        )
        return mat

    def build_g4_volumes(self, volumes_user_info, g4_world_log_vol):
        uiv = volumes_user_info
        for vu in uiv.values():
            # create the volume
            vol = new_element(vu, self.simulation_engine.simulation)
            # construct the G4 Volume
            vol.construct(self, g4_world_log_vol)
            # store at least one PhysVol
            if len(vol.g4_physical_volumes) == 0:
                vol.g4_physical_volumes.append(vol.g4_physical_volume)
            # keep the volume to avoid being destructed
            if g4_world_log_vol is not None:
                n = f"{g4_world_log_vol.GetName()}_{vu.name}"
                self.g4_volumes[n] = vol
            else:
                self.g4_volumes[vu.name] = vol

    # def set_actor_engine(self, actor_engine):
    #     self.actor_engine = actor_engine
    #     for pw in self.parallel_volume_engines:
    #         pw.actor_engine = actor_engine

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # This function is called in MT mode
        tree = self.volumes_tree
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            __world_name__,
            tree,
            self.simulation_engine.simulation.volume_manager,
            self,
        )

    def get_volume(self, name, check_initialization=True):
        if check_initialization and not self.is_constructed:
            fatal(f"Cannot get_volume before initialization")
        try:
            return self.g4_volumes[name]
        except KeyError:
            fatal(
                f"The volume {name} is not in the current "
                f"list of volumes: {self.g4_volumes}"
            )

    def get_database_material_names(self, db=None):
        return self.simulation_engine.simulation.volume_manager.material_database.get_database_material_names(
            db
        )

    def dump_build_materials(self, level=0):
        table = g4.G4Material.GetMaterialTable
        if level == 0:
            names = [m.GetName() for m in table]
            return names
        return table


class VisualisationEngine(EngineBase):
    """
    Main class to manage visualisation
    """

    def __init__(self, simulation_engine):
        self.g4_vis_executive = None
        self.current_visu_filename = None
        self._is_closed = None
        self.simulation_engine = simulation_engine
        self.simulation = simulation_engine.simulation
        EngineBase.__init__(self, self)

    def __del__(self):
        if self.simulation_engine.verbose_destructor:
            warning("Deleting VisualisationEngine")

    def close(self):
        if self.simulation_engine.verbose_close:
            warning(f"Closing VisualisationEngine is_closed = {self._is_closed}")
        self._is_closed = True

    def release_g4_references(self):
        self.g4_vis_executive = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def initialize_visualisation(self):
        ui = self.simulation.user_info
        if not ui.visu:
            return

        # check if filename is set when needed
        if "only" in ui.visu_type and ui.visu_filename is None:
            fatal(f'You must define a visu_filename with "{ui.visu_type}" is set')

        # set the current filename (maybe changed is no visu_filename)
        self.current_visu_filename = ui.visu_filename

        # gdml
        if ui.visu_type == "gdml" or ui.visu_type == "gdml_file_only":
            self.initialize_visualisation_gdml()

        # vrml
        if ui.visu_type == "vrml" or ui.visu_type == "vrml_file_only":
            self.initialize_visualisation_vrml()

        # G4 stuff
        self.g4_vis_executive = g4.G4VisExecutive("all")
        self.g4_vis_executive.Initialize()

    def initialize_visualisation_gdml(self):
        ui = self.simulation.user_info
        # Check when GDML is activated, if G4 was compiled with GDML
        gi = g4.GateInfo
        if not gi.get_G4GDML():
            warning(
                "Visualization with GDML not available in Geant4. Check G4 compilation."
            )
        if self.current_visu_filename is None:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.gdml"

    def initialize_visualisation_vrml(self):
        ui = self.simulation.user_info
        if ui.visu_filename is not None:
            os.environ["G4VRMLFILE_FILE_NAME"] = ui.visu_filename
        else:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.wrl"
            os.environ["G4VRMLFILE_FILE_NAME"] = self.current_visu_filename

    def start_visualisation(self):
        ui = self.simulation.user_info
        if not ui.visu:
            return

        # VRML ?
        if ui.visu_type == "vrml":
            start_vrml_visu(self.current_visu_filename)

        # GDML ?
        if ui.visu_type == "gdml":
            start_gdml_visu(self.current_visu_filename)

        # remove the temporary file
        if ui.visu_filename is None:
            try:
                os.remove(self.current_visu_filename)
            except:
                pass


class SimulationOutput:
    """
    FIXME
    """

    def __init__(self):
        self.simulation = None
        self.actors = {}
        self.sources = {}
        self.sources_by_thread = {}
        self.pid = os.getpid()
        self.ppid = os.getppid()
        self.current_random_seed = None
        self.hook_log = []

    def __del__(self):
        pass

    def store_actors(self, simulation_engine):
        self.actors = simulation_engine.actor_engine.actors
        for actor in self.actors.values():
            actor.close()

    def store_hook_log(self, simulation_engine):
        self.hook_log = simulation_engine.hook_log

    def store_sources(self, simulation_engine):
        self.sources = {}
        s = {}
        source_engine = simulation_engine.source_engine
        ui = simulation_engine.simulation.user_info
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            th = {}
            self.sources_by_thread = [{}] * (ui.number_of_threads + 1)
            for source in source_engine.sources:
                n = source.user_info.name
                if n in th:
                    th[n] += 1
                else:
                    th[n] = 0
                self.sources_by_thread[th[n]][n] = source
        else:
            for source in source_engine.sources:
                s[source.user_info.name] = source
            self.sources = s

    def get_actor(self, name):
        if name not in self.actors:
            s = self.actors.keys
            fatal(f'The actor "{name}" does not exist. Here is the list of actors: {s}')
        return self.actors[name]

    def get_source(self, name):
        ui = self.simulation.user_info
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            return self.get_source_MT(name, 0)
        if name not in self.sources:
            s = self.sources.keys
            fatal(
                f'The source "{name}" does not exist. Here is the list of sources: {s}'
            )
        return self.sources[name]

    def get_source_MT(self, name, thread):
        ui = self.simulation.user_info
        if ui.number_of_threads <= 1 and not ui.force_multithread_mode:
            fatal(f"Cannot use get_source_MT in monothread mode")
        if thread >= len(self.sources_by_thread):
            fatal(
                f"Cannot get source {name} with thread {thread}, while "
                f"there are only {len(self.sources_by_thread)} threads"
            )
        if name not in self.sources_by_thread[thread]:
            s = self.sources_by_thread[thread].keys
            fatal(
                f'The source "{name}" does not exist. Here is the list of sources: {s}'
            )
        return self.sources_by_thread[thread][name]


class SimulationEngine(EngineBase):
    """
    Main class to execute a Simulation (optionally in a separate subProcess)
    """

    def __init__(self, simulation, start_new_process=False):
        self.simulation = simulation
        EngineBase.__init__(self, self)

        # current state of the engine
        self.run_timing_intervals = None
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
        self.visu_engine = None

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
        self.user_hook_after_run = simulation.user_hook_after_run
        # a list to store short log messages
        # produced by hook function such as user_fct_after_init
        self.hook_log = []

    def __del__(self):
        if self.verbose_destructor:
            warning("Deleting SimulationEngine")

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
        if self.visu_engine:
            self.visu_engine.close()

    def release_engines(self):
        self.volume_engine = None
        self.physics_engine = None
        self.source_engine = None
        self.action_engine = None
        self.actor_engine = None
        self.visu_engine = None

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
            warning(f"Closing SimulationEngine is_closed = {self._is_closed}")
        if self._is_closed is False:
            self.close_engines()
            self.release_engines()
            self.release_g4_references()
            self.notify_managers()
            if self.g4_RunManager:
                self.g4_RunManager.SetVerboseLevel(0)
            self.g4_RunManager = None
            self._is_closed = True

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __getstate__(self):
        if self.simulation.verbose_getstate:
            warning("Getstate SimulationEngine")
        self.g4_StateManager = None
        # if self.user_fct_after_init is not None:
        #    gate.warning(f'Warning')
        return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d
        # recreate the StateManager when unpickling
        # because it was set to None during pickling
        self.g4_StateManager = g4.G4StateManager.GetStateManager()

    # define thus as property so the condition can be changed
    # without need to refactor the code
    @property
    def run_multithreaded(self):
        return (
            self.simulation.user_info.number_of_threads > 1
            or self.simulation.user_info.force_multithread_mode
        )

    def start(self):
        # if windows and MT -> fail
        if os.name == "nt" and self.run_multithreaded:
            fatal(
                "Error, the multi-thread option is not available for Windows now. Run the simulation with one thread."
            )
        # prepare sub process
        if self.start_new_process:
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
            # set_start_method("fork", force=True)
            try:
                set_start_method("spawn")
            except RuntimeError:
                pass
            q = Manager().Queue()
            p = Process(target=self.init_and_start, args=(q,))
            p.start()
            p.join()  # (timeout=10)  # timeout might be needed

            try:
                output = q.get(block=False)
            except queue.Empty:
                fatal("Error, the queue is empty, the spawned process probably died.")
        else:
            output = self.init_and_start(None)

        # put back the simulation object to all actors
        for actor in output.actors.values():
            actor.simulation = self.simulation
        output.simulation = self.simulation

        # return the output of the simulation
        return output

    def init_and_start(self, queue):
        """
        When the simulation is about to init, if the Simulation object is in a separate process
        (with 'spawn'), it has been pickled (copied) and the G4 phys list classes does not exist
        anymore, so we need to recreate them with 'create_physics_list_classes'
        Also, the StateManager must be recreated.

        NK: Yes, but not this way. Each class should take care of recreating attributes
        which where set to None during pickling by implementing a __setstate__ method.
        Implementing the resetting somewhere else (maybe in multiple places...) in the code will
        make it very difficult to maintain.

        -> removed the lines and implemented __setstate__ methods for the classes in question
        """

        # initialization
        self.initialize()

        # things to do after init and before run
        self.apply_all_g4_commands()
        if self.user_fct_after_init:
            log.info("Simulation: initialize user fct")
            self.user_fct_after_init(self)

        # go
        self._start()

        # start visualization if vrml or gdml
        self.visu_engine.start_visualisation()
        if self.user_hook_after_run:
            log.info("Simulation: User hook after run")
            self.user_hook_after_run(self)

        # prepare the output
        output = SimulationOutput()
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
        self.volume_engine = VolumeEngine(self)
        self.physics_engine = PhysicsEngine(self)
        self.source_engine = SourceEngine(self)
        self.action_engine = ActionEngine(self)
        self.actor_engine = ActorEngine(self)
        self.visu_engine = VisualisationEngine(self)

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
        assert_run_timing(self.run_timing_intervals)

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

        # Apply G4 commands *before* init (after phys init)
        self.apply_all_g4_commands_before_init()

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
            self.visu_engine.initialize_visualisation()

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
            fatal("DEBUG Register sensitive detector in no MT mode")
            # todo : self.actor_engine.register_sensitive_detectors()

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
            if "MT" not in g4.G4RunManagerFactory.GetOptions():
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
        for command in self.simulation.g4_commands:
            self.apply_g4_command(command)

    def apply_all_g4_commands_before_init(self):
        for command in self.simulation.g4_commands_before_init:
            self.apply_g4_command(command)

    def apply_g4_command(self, command):
        if self.g4_ui is None:
            self.g4_ui = g4.G4UImanager.GetUIpointer()
        log.info(f"Simulation: apply G4 command '{command}'")
        code = self.g4_ui.ApplyCommand(command)
        if code == 0:
            return
        err_codes = {
            0: "fCommandSucceeded",
            100: "fCommandNotFound",
            200: "fIllegalApplicationState",
            300: "fParameterOutOfRange",
            400: "fParameterUnreadable",
            500: "fParameterOutOfCandidates",
            600: "fAliasNotFound",
        }
        closest_err_code = max(filter(lambda x: x <= code, err_codes.keys()))
        closest_err_msg = err_codes[closest_err_code]
        fatal(f'Error in apply_g4_command "{command}": {code} {closest_err_msg}')

    def _start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        s = ""
        if self.start_new_process:
            s = "(in a new process)"
        log.info("-" * 80 + f"\nSimulation: START {s}")

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
            fatal(s)

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
            ui = UIsessionSilent()
        else:
            # Geant4 output with color
            ui = UIsessionVerbose()
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
        fatal(s)

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


def start_gdml_visu(filename):
    try:
        import pyg4ometry
    except Exception as exception:
        warning(exception)
        warning(
            "The module pyg4ometry is maybe not installed or is not working. Try: \n"
            "pip install pyg4ometry"
        )
        return
    r = pyg4ometry.gdml.Reader(filename)
    l = r.getRegistry().getWorldVolume()
    v = pyg4ometry.visualisation.VtkViewerColouredMaterial()
    v.addLogicalVolume(l)
    v.view()


def start_vrml_visu(filename):
    try:
        import pyvista
    except Exception as exception:
        warning(exception)
        warning(
            "The module pyvista is maybe not installed or is not working to be able to visualize vrml files. Try:\n"
            "pip install pyvista"
        )
        return
    pl = pyvista.Plotter()
    pl.import_vrml(filename)
    pl.set_background("black")
    pl.add_axes(line_width=5, color="white")
    pl.show()
