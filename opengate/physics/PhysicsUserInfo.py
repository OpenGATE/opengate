import opengate as gate
import opengate_core as g4
from box import Box

from collections import (
    defaultdict,
)  # NK: I suggest using that instead of Box because it automatically creates nested dictionaries an avoid stupid KeyErrors

# ... or maybe a combination of both, implemented as part of opengate?


class PhysicsUserInfo:
    """
    This class is a simple structure that contains all user general options of ths physics list.

    """

    # def __init__(self, simulation):
    def __init__(
        self, physics_manager
    ):  # the constructor is called from PhysicsManager and receives self
        # keep pointer to ref
        # self.simulation = simulation
        self.simulation = (
            physics_manager.simulation
        )  # NK: should take the simulation attribute from the PhysicsManager object

        # physics list and decay
        self.physics_list_name = None
        self.enable_decay = False

        # options related to the cuts
        self.production_cuts = Box()
        self.energy_range_min = None
        self.energy_range_max = None
        self.apply_cuts = None

        # option related to special user cuts
        self.max_step_size = Box()

        # special case for EM parameters -> G4 object
        self.g4_em_parameters = g4.G4EmParameters.Instance()

    def __del__(self):
        pass

    def __str__(self):
        s = (
            f"{self.physics_list_name}"
            f"apply cuts : {self.apply_cuts}\n"
            f"prod cuts : {self.production_cuts}"
        )
        return s
