import opengate as gate
import opengate_core as g4

# from anytree import LevelOrderIter

from ..Decorators import requires_fatal, requires_warning
from .PhysicsConstructors import UserLimitsPhysics
from opengate_core import G4ApplicationState
from .helpers_physics import translate_particle_name_gate2G4


class PhysicsEngine(gate.EngineBase):
    """
    Class that contains all the information and mechanism regarding physics
    to actually run a simulation. It is associated with a simulation engine.

    """

    def __init__(self, simulation_engine):
        gate.EngineBase.__init__(self)
        # Keep a pointer to the current physics_manager
        self.physics_manager = simulation_engine.simulation.physics_manager

        # keep a pointer to the simulation engine
        # to which this physics engine belongs
        self.simulation_engine = simulation_engine

        # main g4 physic list
        self.g4_physics_list = None
        self.g4_decay = None
        self.g4_radioactive_decay = None
        self.g4_cuts_by_regions = []
        self.g4_em_parameters = None
        self.g4_parallel_world_physics = []

        self.gate_physics_constructors = []

    # def __del__(self):
    #     if self.verbose_destructor:
    #         print("del PhysicsManagerEngine")
    #     pass

    def close(self):
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
        self.simulation_engine.g4_state = G4ApplicationState.G4State_PreInit
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
        self.initialize_em_options()
        self.initialize_user_limits_physics()
        self.initialize_parallel_world_physics()

    def initialize_after_runmanager(self):
        """ """
        # Cuts need to be set *after*
        # G4RunManager.Initialize() is called.
        # Reason: The RunManager would otherwise override
        # the global cuts with the physics list defaults.
        self.initialize_global_cuts()
        self.initialize_regions()
        self.initialize_g4_em_parameters()

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

    def initialize_em_options(self):
        # later
        pass

    def initialize_regions(self):
        for region in self.physics_manager.regions.values():
            region.physics_engine = self
            region.initialize()

    def initialize_global_cuts(self):
        ui = self.physics_manager.user_info

        # range
        if ui.energy_range_min is not None and ui.energy_range_max is not None:
            gate.warning(f"WARNING ! SetEnergyRange only works in MT mode")
            pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
            pct.SetEnergyRange(ui.energy_range_min, ui.energy_range_max)

        # Set global production cuts
        # If value is set for 'all', this overrides individual values
        if ui.global_production_cuts.all is not None:
            # calls SetCutValue for all relevant particles,
            # i.e. proton, gamma, e+, e-
            for pname in self.physics_manager.cut_particle_names.values():
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
        ui = self.physics_manager.user_info
        self.g4_em_parameters = g4.G4EmParameters.Instance()
        self.g4_em_parameters.SetApplyCuts(ui.apply_cuts)

        # FIXME: need to include other em options.

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
