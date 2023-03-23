import opengate as gate
import opengate_core as g4
from anytree import LevelOrderIter

from ..Decorators import requires_fatal
from .PhysicsConstructors import UserLimitsPhysics
from opengate_core import G4ApplicationState
from .helpers_physics import particle_names_gate2g4


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

        # self.gate_physics_constructors = []

    def __del__(self):
        if self.verbose_destructor:
            print("del PhysicsManagerEngine")
        pass

    # make this a property so the communication between
    # PhysicsManager and PhysicsEngine can be changed without
    # impacting this class
    @property
    def user_info_physics_manager(self):
        return self.physics_manager.user_info

    def initialize_before_runmanager(self):
        """Initialize methods to be called *before*
        G4RunManager.InitializePhysics is called.

        """
        self.initialize_physics_list()
        self.initialize_decay()
        self.initialize_em_options()

    def initialize_after_runmanager(self):
        """Initialize methods to be called *after*
        G4RunManager.InitializePhysics is called.
        Reason: The RunManager would otherwise override
        the global cuts with the physics list defaults.

        """
        self.initialize_global_cuts()
        self.initialize_regions()
        self.initialize_user_limits_physics()

    def initialize_physics_list(self):
        """
        Create a Physic List from the Factory
        """
        ui = self.physics_manager.user_info
        pl_name = ui.physics_list_name
        # Select the Physic List: check if simple ones
        if pl_name.startswith("G4"):
            self.g4_physics_list = gate.create_modular_physics_list(pl_name)
        else:
            # If not, select the Physic List from the Factory
            factory = g4.G4PhysListFactory()
            if not factory.IsReferencePhysList(pl_name):
                s = (
                    f"Cannot find the physic list : {pl_name}\n"
                    f"Known list are : {factory.AvailablePhysLists()}\n"
                    f"With EM : {factory.AvailablePhysListsEM()}\n"
                    f"Default is {self.physics_manager.default_physic_list}\n"
                    f"Help : https://geant4-userdoc.web.cern.ch/UsersGuides/PhysicsListGuide/html/physicslistguide.html"
                )
                gate.fatal(s)
            self.g4_physics_list = factory.GetReferencePhysList(pl_name)

    def initialize_decay(self):
        """
        G4DecayPhysics - defines all particles and their decay processes
        G4RadioactiveDecayPhysics - defines radioactiveDecay for GenericIon
        """
        ui = self.physics_manager.user_info
        if not ui.enable_decay:
            return
        # check if decay/radDecay already exist in the physics list
        # (keep p and pp in self to prevent destruction)
        self.g4_decay = self.g4_physics_list.GetPhysics("Decay")
        if not self.g4_decay:
            self.g4_decay = g4.G4DecayPhysics(1)
            self.g4_physics_list.RegisterPhysics(self.g4_decay)
        self.g4_radioactive_decay = self.g4_physics_list.GetPhysics(
            "G4RadioactiveDecay"
        )
        if not self.g4_radioactive_decay:
            self.g4_radioactive_decay = g4.G4RadioactiveDecayPhysics(1)
            self.g4_physics_list.RegisterPhysics(self.g4_radioactive_decay)

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
            self.g4_physics_list.SetDefaultCutValue(ui.global_production_cuts.all)
        else:
            for pname, value in ui.global_production_cuts.items():
                # ignore 'all', as that's already treated above
                if pname == "all":
                    continue
                if value is not None:
                    self.g4_physics_list.SetCutValue(
                        value, particle_names_gate2g4[pname]
                    )

        # # inherit production cuts
        # self.propagate_cuts_to_children(tree)

        # global cuts
        self.g4_em_parameters = g4.G4EmParameters.Instance()
        self.g4_em_parameters.SetApplyCuts(ui.apply_cuts)
        if ui.apply_cuts is False:
            s = f"No production cuts (apply_cuts is False)"
            gate.warning(s)
            gate.fatal(
                "Not implemented: currently it crashes when apply_cuts is False. To be continued ..."
            )
            return

        # # production cuts by region
        # for region in ui.production_cuts:
        #     self.set_region_cut(region)

    @requires_fatal("physics_manager")
    def initialize_user_limits_physics(self):
        if len(self.physics_manager.regions.keys()) > 0:
            # user_limits_physics = UserLimitsPhysics()
            # user_limits_physics.physics_engine = self
            # self.g4_physics_list.RegisterPhysics(user_limits_physics)
            # self.gate_physics_constructors.append(user_limits_physics)

            # Use StepLimiterPhysics from Geant4 for now
            # The costum constructor still segfaults
            self.user_limits_physics = g4.G4StepLimiterPhysics()

    # # def close_down(self):
    # #     self.close_down_physics_constructors()

    # @requires_fatal('simulation_engine')
    # @requires_fatal('g4_physics_list')
    # def close_down_physics_constructors(self):
    #     """This method removes PhysicsConstructors defined in python from the physics list.

    #     It should be called after a simulation run because the RunManager
    #     will otherwise attempt to delete the PhysicsConstructor and cause a segfault.
    #     """
    #     current_state = self.simulation_engine.g4_state
    #     self.simulation_engine.g4_state = G4ApplicationState.G4State_PreInit
    #     for pc in self.gate_physics_constructors:
    #         self.g4_physics_list.RemovePhysics(pc)
    #     self.simulation_engine.g4_state = current_state

    # def propagate_cuts_to_child(self, tree):
    #     """This method is kept for legacy compatibility
    #     because the method name was changed to
    #     propagate_cuts_to_children.
    #     Should be deleted soon.

    #     """
    #     print(10 * "*" + 10 * "#" + 10 * "*")
    #     print("Old propagate_cuts_to_child method invoked. Please update the code.")
    #     print(10 * "*" + 10 * "#" + 10 * "*")
    #     self.propagate_cuts_to_children(tree)

    # def propagate_cuts_to_children(self, tree):
    #     ui = self.physics_manager.user_info
    #     pc = ui.production_cuts
    #     # loop on the tree, level order
    #     for node in LevelOrderIter(tree[gate.__world_name__]):
    #         if not node.parent:
    #             # this is the world, do nothing
    #             continue
    #         # get the user cuts for this region
    #         if node.name in pc:
    #             cuts = pc[node.name]
    #         else:
    #             gate.fatal(f"Cannot find region {node.name} in the cuts list: {pc}")
    #         # get the cuts for the parent
    #         if node.parent.name in pc:
    #             pcuts = pc[node.parent.name]
    #         else:
    #             gate.fatal(
    #                 f"Cannot find parent region {node.parent.name} in the cuts list: {pc}"
    #             )
    #         for p in self.physics_manager.cut_particle_names:
    #             # set the cut for the current region like the parent
    #             # but only if it was not set by user
    #             if p not in cuts:
    #                 if p in pcuts:
    #                     cuts[p] = pcuts[p]
    #                 else:
    #                     # special case when the parent=world, with default cuts
    #                     cuts[p] = -1
    #                     pcuts[p] = -1
