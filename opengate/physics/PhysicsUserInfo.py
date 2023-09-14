import opengate_core as g4
from box import Box
from .PhysicsManager import PhysicsManager
from .PhysicsListManager import PhysicsListManager
from ..helpers import fatal


class PhysicsUserInfo:
    """
    This class is a simple structure that contains all user general options of ths physics list.

    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # physics list and optional physics constructors
        self.physics_list_name = None
        # dictionary with names of additional physics constructors
        # to be added to physics list (False = off by default)
        # content is maintained by the PhysicsListManager
        self.special_physics_constructors = Box()
        for spc in PhysicsListManager.special_physics_constructor_classes:
            self.special_physics_constructors[spc] = False

        # options related to the cuts and user limits
        # self.production_cuts = Box()
        self.global_production_cuts = Box()
        self.global_production_cuts.all = None
        for pname in PhysicsManager.cut_particle_names.keys():
            self.global_production_cuts[pname] = None
        self.energy_range_min = None
        self.energy_range_max = None
        self.apply_cuts = True

        # Dictionary of particles for which the user
        # can decide whethr to apply user limits
        self.user_limits_particles = {}
        self.user_limits_particles["all"] = False
        # "all_charged" = True corresponds to the logic in the G4StepLimiterPhysics
        self.user_limits_particles["all_charged"] = True
        self.user_limits_particles["gamma"] = False
        self.user_limits_particles["electron"] = False
        self.user_limits_particles["positron"] = False
        self.user_limits_particles["proton"] = False

        # # special case for EM parameters -> G4 object
        # # self.g4_em_parameters = g4.G4EmParameters.Instance()
        # self.em_parameters = Box()
        # self.em_parameters["fluo"] = False
        # self.em_parameters["auger"] = False
        # self.em_parameters["auger_cascade"] = False
        # self.em_parameters["pixe"] = False
        # self.em_parameters["deexcitation_ignore_cut"] = False

    def __del__(self):
        pass

    def __str__(self):
        s = (
            f"{self.physics_list_name}"
            f"apply cuts : {self.apply_cuts}\n"
            f"global prod cuts : {self.global_production_cuts}"
            f"user limits particles : {self.user_limits_particles}"
        )
        return s
