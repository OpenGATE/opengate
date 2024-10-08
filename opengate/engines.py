import time
import random
import sys
import os
import weakref
from box import Box
from anytree import PreOrderIter

import opengate_core as g4
from .exception import fatal, warning, GateImplementationError
from .decorators import requires_fatal, requires_warning
from .logger import log
from .runtiming import assert_run_timing
from .uisessions import UIsessionSilent, UIsessionVerbose
from .exception import ExceptionHandler
from .element import new_element
from .physics import (
    UserLimitsPhysics,
    translate_particle_name_gate_to_geant4,
    cut_particle_names,
    create_g4_optical_properties_table,
    load_optical_properties_from_xml,
)
from .base import GateSingletonFatal


class EngineBase:
    """
    Base class for all engines (SimulationEngine, VolumeEngine, etc.)
    """

    def __init__(self, simulation_engine):
        self.simulation_engine = simulation_engine
        # debug verbose
        self.verbose_getstate = simulation_engine.verbose_getstate
        self.verbose_close = simulation_engine.verbose_close

    def close(self):
        self.simulation_engine = None

    def __getstate__(self):
        raise GateImplementationError(
            f"The __getstate__() method of the {type(self).__name__} class got called. "
            f"That should not happen because it should be closed before anything is pickled "
            f"at the end of a subprocess. Check warning messages for clues!"
        )


class SourceEngine(EngineBase):
    """
    Source Engine manages the G4 objects of sources at runtime
    """

    # G4RunManager::BeamOn takes an int as input. The max cpp int value is currently 2147483647
    # Python manages int differently (no limit), so we need to set the max value here.
    max_int = 2147483647

    def __init__(self, simulation_engine):
        super().__init__(simulation_engine)

        # Keep a pointer to the current simulation
        # self.source_manager = source_manager
        self.simulation_engine = simulation_engine

        # List of run time intervals
        self.run_timing_intervals = None
        self.current_run_interval = None

        # use a progress bar ?
        self.progress_bar = False
        self.expected_number_of_events = "unknown"

        # List of sources (GateSource), for all threads
        self.sources = []

        # The source manager will be constructed at build (during ActionManager)
        # Its task is to call GeneratePrimaries and loop over the sources
        # For MT, the master_source_manager is the MasterThread
        # The g4_thread_source_managers list all master sources for all threads
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = []

        # Options dict for cpp SourceManager
        # will be set in create_g4_source_manager
        # FIXME: Why is this separate dictionary needed? Would be better to access the source manager directly
        self.source_manager_options = Box()

    def close(self):
        if self.verbose_close:
            warning(f"Closing SourceEngine")
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = None
        # a source object contains a reference to a G4 source
        self.sources = None

    def initialize(self, run_timing_intervals, progress_bar=False):
        self.run_timing_intervals = run_timing_intervals
        assert_run_timing(self.run_timing_intervals)
        if len(self.simulation_engine.simulation.source_manager.user_info_sources) == 0:
            self.simulation_engine.simulation.warn_user(
                f"No source: no particle will be generated"
            )
        self.progress_bar = progress_bar

    def initialize_actors(self):
        """
        Parameters
        ----------
        actors : dict
            The dictionary ActorEngine.actors which contains key-value pairs
            "actor_name" : "Actor object"
        """
        self.g4_master_source_manager.SetActors(
            self.simulation_engine.simulation.actor_manager.sorted_actors
        )

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
            source.add_to_source_manager(ms)
            source.initialize(self.run_timing_intervals)
            self.sources.append(source)

        # Copy visualization parameters
        for k, v in self.simulation_engine.simulation.user_info.items():
            if "visu" in k:
                self.source_manager_options[k] = v

        # Copy verbosity parameters
        for k, v in self.simulation_engine.simulation.user_info.items():
            if "verbose_" in k:
                self.source_manager_options[k] = v

        # progress bar
        self.source_manager_options["progress_bar"] = (
            self.simulation_engine.simulation.progress_bar
        )

        ms.Initialize(self.run_timing_intervals, self.source_manager_options)
        self.expected_number_of_events = (
            ms.GetExpectedNumberOfEvents()
            * self.simulation_engine.simulation.number_of_threads
        )
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
        # FIXME (2) : check estimated nb of particle, warning if too large
        # start the master thread (only main thread)
        self.g4_master_source_manager.StartMasterThread()

        # once terminated, packup the sources (if needed)
        for source in self.sources:
            source.prepare_output()

    def can_predict_expected_number_of_event(self):
        can_predict = True
        for source in self.sources:
            can_predict = can_predict and source.can_predict_number_of_events()
        return can_predict


class PhysicsEngine(EngineBase):
    """
    Class that contains all the information and mechanism regarding physics
    to actually run a simulation. It is associated with a simulation engine.

    """

    def __init__(self, *args):
        super().__init__(*args)
        # Keep a shortcut reference to the current physics_manager
        self.physics_manager = self.simulation_engine.simulation.physics_manager

        # Register this engine with the regions
        for region in self.physics_manager.regions.values():
            region.physics_engine = self

        for optical_surface in self.physics_manager.optical_surfaces.values():
            optical_surface.physics_engine = self

        # main g4 physic list
        self.g4_physics_list = None
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = []
        self.g4_em_parameters = None
        self.g4_parallel_world_physics = []
        self.g4_optical_material_tables = {}
        self.g4_physical_volumes = []
        self.g4_surface_properties = None

        # We need to keep a reference to physics constructors
        # implemented on the python side
        # Physics constructor linked via pybind have the nodelete pointer option,
        # so python will not delete them and no reference needs to be kept
        self.gate_physics_constructors = []

        self.optical_surfaces_properties_dict = {}

    def close(self):
        if self.verbose_close:
            warning(f"Closing PhysicsEngine")
        self.close_physics_constructors()
        self.release_g4_references()
        self.release_optical_surface_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_physics_list = None
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = None
        self.g4_em_parameters = None
        self.g4_parallel_world_physics = []
        self.g4_optical_material_tables = {}
        self.g4_physical_volumes = []
        self.g4_surface_properties = None

    def release_optical_surface_g4_references(self):
        for optical_surface in self.physics_manager.optical_surfaces.values():
            optical_surface.release_g4_references()

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
        self.initialize_physics_biasing()
        self.initialize_parallel_world_physics()

    def initialize_after_runmanager(self):
        """ """
        # Cuts need to be set *after*
        # G4RunManager.Initialize() is called.
        # Reason: The Initialize() sequence would otherwise override
        # the global cuts with the physics list defaults.
        self.initialize_global_cuts()
        self.initialize_regions()
        self.initialize_optical_material_properties()
        self.initialize_optical_surfaces()

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
            self.physics_manager.warn_user(
                f"WARNING ! SetEnergyRange only works in MT mode"
            )
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
                        value, translate_particle_name_gate_to_geant4(pname)
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

    def initialize_physics_biasing(self):
        # get a dictionary {particle:[processes]}
        particles_processes = self.physics_manager.get_biasing_particles_and_processes()

        # check if there are any processes requested for any particle
        if any([len(v) > 0 for v in particles_processes.values()]):
            g4_biasing_physics = g4.G4GenericBiasingPhysics()
            for particle, processes in particles_processes.items():
                if len(processes) > 0:
                    g4_biasing_physics.PhysicsBias(particle, processes)
            self.g4_physics_list.RegisterPhysics(g4_biasing_physics)

    # This function deals with calling the parse function
    # and setting the returned MaterialPropertyTable to G4Material object
    def initialize_optical_material_properties(self):
        # Load optical material properties if special physics constructor "G4OpticalPhysics"
        # is set to True in PhysicsManager's user info
        if (
            self.simulation_engine.simulation.physics_manager.special_physics_constructors.G4OpticalPhysics
            is True
        ):
            # retrieve path to file from physics manager
            for (
                vol
            ) in self.simulation_engine.simulation.volume_manager.volumes.values():
                material_name = vol.g4_material.GetName()
                material_properties = load_optical_properties_from_xml(
                    self.physics_manager.optical_properties_file, material_name
                )
                if material_properties is not None:
                    self.g4_optical_material_tables[str(material_name)] = (
                        create_g4_optical_properties_table(material_properties)
                    )
                    vol.g4_material.SetMaterialPropertiesTable(
                        self.g4_optical_material_tables[str(material_name)]
                    )
                else:
                    self.simulation_engine.simulation.warn_user(
                        f"Could not load the optical material properties for material {material_name} "
                        f"found in volume {vol.name} from file {self.physics_manager.optical_properties_file}."
                    )

    @requires_fatal("physics_manager")
    def initialize_optical_surfaces(self):
        """Calls initialize() method of each OpticalSurface instance."""

        # Call the initialize() method in OpticalSurface class to
        # create the related G4 instances.
        for optical_surface in self.physics_manager.optical_surfaces.values():
            optical_surface.initialize()

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

    def __init__(self, *args):
        g4.G4VUserActionInitialization.__init__(self)
        EngineBase.__init__(self, *args)

        # *** G4 references ***
        # List of G4 source managers (one per thread)
        self.g4_PrimaryGenerator = []

        # The main G4 source manager
        self.g4_main_PrimaryGenerator = None

        # Lists of elements to prevent destruction
        self.g4_RunAction = []
        self.g4_EventAction = []
        self.g4_TrackingAction = []

    def close(self):
        if self.verbose_close:
            warning(f"Closing ActionEngine")
        self.release_g4_references()
        super().close()

    def release_g4_references(self):
        self.g4_PrimaryGenerator = []
        self.g4_main_PrimaryGenerator = None
        self.g4_RunAction = []
        self.g4_EventAction = []
        self.g4_TrackingAction = []

    def register_all_actions(self, actor):
        self.register_run_actions(actor)
        self.register_event_actions(actor)
        self.register_tracking_actions(actor)

    def register_run_actions(self, actor):
        for ra in self.g4_RunAction:
            ra.RegisterActor(actor)

    def register_event_actions(self, actor):
        for ea in self.g4_EventAction:
            ea.RegisterActor(actor)

    def register_tracking_actions(self, actor):
        for ta in self.g4_TrackingAction:
            ta.RegisterActor(actor)

    def BuildForMaster(self):
        # This function is called only in MT mode, for the master thread
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


def register_sensitive_detector_to_children(actor, lv):
    log.debug(
        f'Actor: "{actor.user_info.name}" '
        f'(attached to "{actor.attached_to}") '
        f'set to volume "{lv.GetName()}"'
    )
    actor.RegisterSD(lv)
    for i in range(lv.GetNoDaughters()):
        child = lv.GetDaughter(i).GetLogicalVolume()
        register_sensitive_detector_to_children(actor, child)


class ActorEngine(EngineBase):
    """
    This object manages all actors G4 objects at runtime
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_to_actors()

    @property
    def actor_manager(self):
        return self.simulation_engine.simulation.actor_manager

    def close(self):
        if self.verbose_close:
            warning(f"Closing ActorEngine")
        for actor in self.actor_manager.actors.values():
            actor.close()
        super().close()

    def initialize(self):
        for actor in self.actor_manager.sorted_actors:
            log.debug(f"Actor: initialize [{actor.type_name}] {actor.name}")
            self.simulation_engine.action_engine.register_all_actions(actor)
            actor.initialize()
            # warning : the step actions will be registered by register_sensitive_detectors
            # called by ConstructSDandField

    def register_to_actors(self):
        for actor in self.actor_manager.actors.values():
            actor.actor_engine = self

    def register_sensitive_detectors(self, world_name):
        for actor in self.actor_manager.sorted_actors:
            if actor.IsSensitiveDetector() is True:
                # Step: only enabled if attachTo a given volume.
                # Propagated to all child and sub-child
                # tree = volume_manager.volumes_tree
                if isinstance(actor.attached_to, str):
                    # make a list with one single element
                    mothers = [actor.attached_to]
                else:
                    mothers = actor.attached_to
                # add SD for all mothers
                for volume_name in mothers:
                    volume = (
                        self.simulation_engine.simulation.volume_manager.get_volume(
                            volume_name
                        )
                    )
                    if volume.world_volume.name == world_name:
                        register_sensitive_detector_to_children(
                            actor, volume.g4_logical_volume
                        )

    def start_simulation(self):
        # consider the priority value of the actors
        for actor in self.actor_manager.sorted_actors:
            actor.StartSimulationAction()

    def stop_simulation(self):
        # consider the priority value of the actors
        for actor in self.actor_manager.sorted_actors:
            actor.EndSimulationAction()


class FilterEngine(EngineBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def filter_manager(self):
        return self.simulation_engine.simulation.filter_manager

    def initialize(self):
        for f in self.filter_manager.filters.values():
            f.initialize()

    def close(self):
        for f in self.filter_manager.filters.values():
            f.close()
        super().close()


class ParallelWorldEngine(g4.G4VUserParallelWorld, EngineBase):
    """FIXME: Doc ParallelWorldEngine"""

    def __init__(self, parallel_world_name, *args):
        g4.G4VUserParallelWorld.__init__(self, parallel_world_name)
        EngineBase.__init__(self, *args)

        # keep input data
        self.parallel_world_name = parallel_world_name
        # the parallel world volume needs the engine to construct itself
        self.parallel_world_volume.parallel_world_engine = self

    def close(self):
        self.parallel_world_volume.parallel_world_engine = None
        super().close()

    @property
    def parallel_world_volume(self):
        return (
            self.simulation_engine.volume_engine.volume_manager.parallel_world_volumes[
                self.parallel_world_name
            ]
        )

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserParallelWorld
        """

        # Construct all volumes within this world along the tree hierarchy
        # The world volume of this world is the first item
        for volume in PreOrderIter(self.parallel_world_volume):
            volume.construct()

    def ConstructSD(self):
        # FIXME
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            self.parallel_world_name,
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

        self._is_constructed = False

        self.volume_manager = self.simulation_engine.simulation.volume_manager

        # parallel world engines will be created by the simulation engine
        self.parallel_world_engines = {}

        # Make sure all volumes have a reference to this engine
        self.register_to_volumes()

    def create_parallel_world_engines(self):
        for parallel_world_name in self.volume_manager.parallel_world_names:
            self.parallel_world_engines[parallel_world_name] = ParallelWorldEngine(
                parallel_world_name, self.simulation_engine
            )
            self.RegisterParallelWorld(self.parallel_world_engines[parallel_world_name])

    def register_to_volumes(self):
        for v in self.volume_manager.volumes.values():
            v.volume_engine = self

    def close(self):
        for vol in self.volume_manager.volumes.values():
            vol.close()
        for pwv in self.volume_manager.parallel_world_volumes.values():
            pwv.close()
        for pwe in self.parallel_world_engines.values():
            pwe.close()
        self.parallel_world_engines = {}
        super().close()

    def initialize(self):
        # build the materials
        self.simulation_engine.simulation.volume_manager.material_database.initialize()
        # initialize actors which handle dynamic volume parametrization, e.g. MotionActors
        self.initialize_dynamic_parametrisations()

    def initialize_dynamic_parametrisations(self):
        dynamic_volumes = self.volume_manager.dynamic_volumes
        if len(dynamic_volumes) > 0:
            dynamic_geometry_actor = self.simulation_engine.simulation.add_actor(
                "DynamicGeometryActor", "dynamic_geometry_actor"
            )
            dynamic_geometry_actor.priority = 0
            for vol in self.volume_manager.dynamic_volumes:
                dynamic_geometry_actor.geometry_changers.extend(vol.create_changers())

    def Construct(self):
        """
        G4 overloaded.
        Override the Construct method from G4VUserDetectorConstruction
        """

        # # build the materials
        # # FIXME: should go into initialize method
        # self.simulation_engine.simulation.volume_manager.material_database.initialize()

        # Construct all volumes within the mass world along the tree hierarchy
        # The world volume is the first item

        self.volume_manager.update_volume_tree()
        for volume in PreOrderIter(self.volume_manager.world_volume):
            volume.construct()

        # return the (main) world physical volume
        self._is_constructed = True
        return self.volume_manager.world_volume.g4_physical_volume

    def check_overlaps(self, verbose):
        for volume in self.volume_manager.volumes.values():
            if volume not in self.volume_manager.all_world_volumes:
                for pw in volume.g4_physical_volumes:
                    try:
                        b = pw.CheckOverlaps(1000, 0, verbose, 1)
                        if b:
                            fatal(
                                f'Some volumes overlap with the volume "{volume.name}". \n'
                                f"Use Geant4's verbose output to know which ones. \n"
                                f"Aborting."
                            )
                    # FIXME: What causes the exceptions?
                    except:
                        warning(f"Could not check overlap for volume {volume.name}.")

    def ConstructSDandField(self):
        """
        G4 overloaded
        """
        # This function is called in MT mode
        self.simulation_engine.actor_engine.register_sensitive_detectors(
            self.volume_manager.world_volume.name,
        )

    def get_volume(self, name):
        return self.volume_manager.get_volume(name)

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
        EngineBase.__init__(self, simulation_engine)
        self.g4_vis_executive = None
        self.current_visu_filename = None
        self._is_closed = None
        self.simulation = simulation_engine.simulation

    def close(self):
        if self.simulation_engine.verbose_close:
            warning(f"Closing VisualisationEngine is_closed = {self._is_closed}")
        # self.release_g4_references()
        self._is_closed = True

    def release_g4_references(self):
        self.g4_vis_executive = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def initialize_visualisation(self):
        # check if filename is set when needed
        if (
            "only" in self.simulation.visu_type
            and self.simulation.visu_filename is None
        ):
            fatal(
                f'You must define a visu_filename with "{self.simulation.visu_type}" is set'
            )

        # set the current filename (maybe changed is no visu_filename)
        self.current_visu_filename = self.simulation.visu_filename

        # gdml
        if self.simulation.visu_type in ("gdml", "gdml_file_only"):
            self.initialize_visualisation_gdml()

        # vrml
        if self.simulation.visu_type in ("vrml", "vrml_file_only"):
            self.initialize_visualisation_vrml()

        # G4 stuff
        self.g4_vis_executive = g4.G4VisExecutive("all")
        self.g4_vis_executive.Initialize()

    def initialize_visualisation_gdml(self):
        # Check when GDML is activated, if G4 was compiled with GDML
        if not g4.GateInfo.get_G4GDML():
            self.simulation.warn_user(
                "Visualization with GDML not available in Geant4. Check G4 compilation."
            )
        if self.current_visu_filename is None:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.gdml"

    def initialize_visualisation_vrml(self):
        if self.simulation.visu_filename is not None:
            os.environ["G4VRMLFILE_FILE_NAME"] = self.simulation.visu_filename
        else:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.wrl"
            os.environ["G4VRMLFILE_FILE_NAME"] = self.current_visu_filename

    def start_visualisation(self):
        if not self.simulation.visu:
            return

        # VRML ?
        if self.simulation.visu_type == "vrml":
            start_vrml_visu(self.current_visu_filename)

        # GDML ?
        if self.simulation.visu_type == "gdml":
            start_gdml_visu(self.current_visu_filename)

        # remove the temporary file
        if self.simulation.visu_filename is None:
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
        self.user_hook_log = []
        self.warnings = None

    def store_actors(self, simulation_engine):
        self.actors = simulation_engine.simulation.actor_manager.actors
        for actor in self.actors.values():
            actor.close()

    def store_hook_log(self, simulation_engine):
        self.user_hook_log = simulation_engine.user_hook_log

    def store_sources(self, simulation_engine):
        self.sources = {}
        if simulation_engine.simulation.multithreaded is True:
            th = {}
            self.sources_by_thread = [{}] * (
                simulation_engine.simulation.number_of_threads + 1
            )
            for source in simulation_engine.source_engine.sources:
                n = source.user_info.name
                if n in th:
                    th[n] += 1
                else:
                    th[n] = 0
                self.sources_by_thread[th[n]][n] = source
        else:
            s = {}
            for source in simulation_engine.source_engine.sources:
                s[source.user_info.name] = source
            self.sources = s

    def get_actor(self, name):
        if name not in self.actors:
            fatal(
                f'The actor "{name}" does not exist. '
                f"These are the actors known to this simulation: {list(self.actors.keys())}"
            )
        return self.actors[name]

    def get_source(self, name):
        if name not in self.sources:
            fatal(
                f'The source "{name}" does not exist. Here is the list of sources: {list(self.sources.keys())}'
            )
        return self.sources[name]

    def get_source_mt(self, name, thread):
        if (
            self.simulation.number_of_threads <= 1
            and not self.simulation.force_multithread_mode
        ):
            fatal(f"Cannot use get_source_mt in monothread mode")
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


class SimulationEngine(GateSingletonFatal):
    """
    Main class to execute a Simulation. Can only be created once per process because Geant4 dictates so.
    """

    def __init__(self, simulation, new_process=False):
        self.simulation = simulation
        self.verbose_getstate = simulation.verbose_getstate
        self.verbose_close = simulation.verbose_close

        # create engines passing the simulation engine (self) as argument
        self.volume_engine = VolumeEngine(self)
        self.volume_engine.create_parallel_world_engines()
        self.physics_engine = PhysicsEngine(self)
        self.source_engine = SourceEngine(self)
        self.action_engine = ActionEngine(self)
        self.actor_engine = ActorEngine(self)
        self.filter_engine = FilterEngine(self)
        self.visu_engine = VisualisationEngine(self)

        # current state of the engine
        self.run_timing_intervals = None
        self.is_initialized = False

        # do we create a subprocess or not ?
        # this is only for info.
        # Process handling is done in Simulation class, not in SimulationEngine!
        self.new_process = new_process

        # LATER : option to wait the end of completion or not

        # UI
        self.g4_ui_session = None
        self.g4_ui = None

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
        self.user_hook_after_init = simulation.user_hook_after_init
        self.user_hook_after_run = simulation.user_hook_after_run
        # a list to store short log messages
        # produced by hook function such as user_hook_after_init
        self.user_hook_log = []  # FIXME: turn this into dictionary

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
        self.g4_ui_session = None
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
            self._is_closed = True
        self.g4_RunManager = None

    def __enter__(self):
        return self

    def __exit__(self, _type, value, traceback):
        self.close()

    def __getstate__(self):
        raise GateImplementationError(
            "The __getstate__() method of the SimulationEngine class got called. "
            "That should not happen because it should be closed before anything is pickled "
            "at the end of a subprocess. Check warning messages for clues!"
        )
        # if self.simulation.verbose_getstate:
        #     warning("Getstate SimulationEngine")
        # self.g4_StateManager = None
        # # if self.user_fct_after_init is not None:
        # #    gate.warning(f'Warning')
        # return self.__dict__

    def __setstate__(self, d):
        self.__dict__ = d
        # recreate the StateManager when unpickling
        # because it was set to None during pickling
        self.g4_StateManager = g4.G4StateManager.GetStateManager()

    def run_engine(self):
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

        # prepare the output
        output = SimulationOutput()

        # if the simulation is run in a subprocess,
        # we want to capture only the warnings from this point on
        # because everything else has already been executed in the main process
        # and potential warnings have already been registered.
        if self.new_process is True:
            self.simulation.reset_warnings()

        # initialization
        self.initialize()

        # things to do after init and before run
        self.apply_all_g4_commands_after_init()
        if self.user_hook_after_init:
            log.info("Simulation: initialize user fct")
            self.user_hook_after_init(self)

        # if init only, we stop
        if self.simulation.init_only:
            output.store_actors(self)
            output.store_sources(self)
            output.store_hook_log(self)
            output.current_random_seed = self.current_random_seed
            output.expected_number_of_events = (
                self.source_engine.expected_number_of_events
            )
            return output

        # go
        self.start_and_stop()

        # start visualization if vrml or gdml
        self.visu_engine.start_visualisation()
        if self.user_hook_after_run:
            log.info("Simulation: User hook after run")
            self.user_hook_after_run(self)

        # prepare the output
        output.store_actors(self)
        output.store_sources(self)
        output.store_hook_log(self)
        output.current_random_seed = self.current_random_seed
        output.expected_number_of_events = self.source_engine.expected_number_of_events
        output.warnings = self.simulation.warnings

        return output

    def start_and_stop(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        s = ""
        if self.new_process:
            s = "(in a new process) "
        s2 = ""
        if self.simulation.progress_bar:
            n = self.source_engine.expected_number_of_events
            if self.source_engine.can_predict_expected_number_of_event():
                s2 = f"(around {n} events expected)"
            else:
                s2 = f"(cannot predict the number of events, max is {n}, e.g. acceptance_angle is enabled)"
        log.info("-" * 80 + f"\nSimulation: START {s}{s2}")

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
        engine_name = self.simulation.random_engine
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
        if self.simulation.random_seed == "auto":
            self.current_random_seed = random.randrange(sys.maxsize)
        else:
            self.current_random_seed = self.simulation.random_seed

        # if windows, the long are 4 bytes instead of 8 bytes for python and unix system
        if os.name == "nt":
            self.current_random_seed = int(
                self.current_random_seed % ((pow(2, 32) - 1) / 2)
            )

        # set the seed
        g4.G4Random.setTheSeed(self.current_random_seed, 0)

    def initialize_g4_verbose(self):
        if self.simulation.g4_verbose:
            # Geant4 output with color
            ui = UIsessionVerbose()
            # set verbose tracking according to user info:
        else:
            # no Geant4 output
            ui = UIsessionSilent()
        if self.simulation.g4_verbose_level_tracking >= 0:
            self.simulation.g4_commands_after_init.append(
                f"/tracking/verbose {self.simulation.g4_verbose_level_tracking}"
            )
        # it is also possible to set ui=None for 'default' output
        # we must keep a ref to ui_session
        self.g4_ui_session = ui
        # we must keep a ref to ui_manager
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        if self.g4_ui is None:
            fatal("Unable to obtain a UIpointer")
        self.g4_ui.SetCoutDestination(ui)

    def initialize(self):
        """
        Build the main geant4 objects and initialize them.
        """

        # g4 verbose
        self.initialize_g4_verbose()

        # visualisation ?
        # self.pre_init_visu()

        # init random engine (before the MTRunManager creation)
        self.initialize_random_engine()

        # Some sources (e.g. PHID) need to perform computation once everything is defined in user_info but *before* the
        # initialization of the G4 engine starts. This can be done via this function.
        self.simulation.initialize_source_before_g4_engine()

        # create the run manager (assigned to self.g4_RunManager)
        if self.g4_RunManager:
            fatal("A G4RunManager as already been created.")
        self.g4_RunManager = self.create_run_manager()
        # this creates a finalizer for the run manager which assures that
        # the close() method is called before the run manager is garbage collected,
        # i.e. G4RunManager destructor is called
        self.run_manager_finalizer = weakref.finalize(self.g4_RunManager, self.close)

        # create the handler for the exception
        self.g4_exception_handler = ExceptionHandler()

        # check run timing
        self.run_timing_intervals = self.simulation.run_timing_intervals.copy()
        # FIXME: put this assertion in a setter hook
        assert_run_timing(self.run_timing_intervals)

        # check if some actors need UserEventInformation
        # FIXME: should go to ActorEngine
        self.initialize_user_event_information_flag()

        # Geometry initialization
        log.info("Simulation: initialize Geometry")
        self.volume_engine.initialize()

        # Physics initialization
        log.info("Simulation: initialize Physics")
        self.physics_engine.initialize_before_runmanager()

        # Apply G4 commands *before* init (after phys init)
        self.apply_all_g4_commands_before_init()

        # sources
        log.info("Simulation: initialize Source")
        self.source_engine.initialize(
            self.simulation.run_timing_intervals, self.simulation.progress_bar
        )

        # action

        # Visu
        if self.simulation.visu:
            log.info("Simulation: initialize Visualization")
            self.visu_engine.initialize_visualisation()

        # set pointers to python classes
        self.g4_RunManager.SetUserInitialization(self.volume_engine)
        self.g4_RunManager.SetUserInitialization(self.physics_engine.g4_physics_list)
        self.g4_RunManager.SetUserInitialization(
            self.action_engine
        )  # G4 internally calls action_engine.Build()

        # Important: The volumes are constructed
        # when the G4RunManager calls the Construct method of the VolumeEngine,
        # which happens in the InitializeGeometry() method of the
        # G4RunManager within Initialize() (Geant4 code)

        # Note: In serial mode, SetUserInitialization() would only be needed
        # for geometry and physics, but in MT mode the fake run for worker
        # initialization needs a particle source.
        log.info("Simulation: initialize G4RunManager")
        if self.simulation.multithreaded is True:
            self.g4_RunManager.InitializeWithoutFakeRun()
        else:
            self.g4_RunManager.Initialize()

        log.info("Simulation: initialize PhysicsEngine after RunManager initialization")
        self.physics_engine.initialize_after_runmanager()
        self.g4_RunManager.PhysicsHasBeenModified()

        # G4's MT RunManager needs an empty run to initialize workers
        if self.simulation.multithreaded is True:
            self.g4_RunManager.FakeBeamOn()

        # Actions initialization
        # This must come after the G4RunManager initialization
        # because the RM initialization calls ActionEngine.Build()
        # which is required for initialize()
        # Actors initialization (before the RunManager Initialize)
        # self.actor_engine.create_actors()  # calls the actors' constructors
        log.info("Simulation: initialize actors")
        self.source_engine.initialize_actors()
        self.actor_engine.initialize()
        self.filter_engine.initialize()

        self.is_initialized = True

        # Check overlaps
        if self.simulation.check_volumes_overlap:
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
        if self.simulation.multithreaded is True:
            # GetOptions() returns a set which should contain 'MT'
            # if Geant4 was compiled with G4MULTITHREADED
            if "MT" not in g4.G4RunManagerFactory.GetOptions():
                fatal(
                    "Geant4 does not support multithreading. Probably it was compiled without G4MULTITHREADED flag."
                )

            log.info(
                f"Simulation: create MTRunManager with {self.simulation.number_of_threads} threads"
            )
            g4_RunManager = g4.WrappedG4MTRunManager()
            g4_RunManager.SetNumberOfThreads(self.simulation.number_of_threads)
        else:
            log.info("Simulation: create RunManager (single thread)")
            g4_RunManager = g4.WrappedG4RunManager()

        if g4_RunManager is None:
            fatal("Unable to create RunManager")

        g4_RunManager.SetVerboseLevel(self.simulation.g4_verbose_level)
        return g4_RunManager

    def apply_all_g4_commands_after_init(self):
        for command in self.simulation.g4_commands_after_init:
            self.add_g4_command_after_init(command)

    def apply_all_g4_commands_before_init(self):
        for command in self.simulation.g4_commands_before_init:
            self.add_g4_command_after_init(command)

    def add_g4_command_after_init(self, command):
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

    def check_volumes_overlap(self, verbose=True):
        # we need to 'cheat' the verbosity before doing the check
        b = self.simulation.g4_verbose
        self.simulation.g4_verbose = True
        self.initialize_g4_verbose()

        # check
        self.volume_engine.check_overlaps(verbose)

        # put back verbosity
        self.simulation.g4_verbose = b
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

    def initialize_user_event_information_flag(self):
        self.user_event_information_flag = False
        for ac in self.simulation.actor_manager.actors.values():
            if "attributes" in ac.user_info:
                if "ParentParticleName" in ac.attributes:
                    self.user_event_information_flag = True


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
