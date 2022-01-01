import gam_gate as gam
import gam_g4 as g4
from box import Box


class PhysicsUserInfo:
    """
        This class is a simple structure that contains all user general options of ths physics list.

    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # physics list and decay
        self.physics_list_name = None
        self.enable_decay = False

        # options related to the cuts # FIXME may change
        self.production_cuts = Box()
        self.energy_range_min = None
        self.energy_range_max = None
        self.apply_cuts = None

        # special case for EM parameters -> G4 object
        self.g4_em_parameters = g4.G4EmParameters.Instance()

    def __del__(self):
        pass

    def __str__(self):
        s = f'{self.physics_list_name}' \
            f'apply cuts : {self.apply_cuts}\n' \
            f'prod cuts : {self.production_cuts}'
        return s
