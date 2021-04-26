import gam
import gam_g4 as g4
from box import Box


class SimulationUserInfo:
    """
        This class is a simple structure that contains all user general options of a simulation.
    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # Geant4 verbose
        self.g4_verbose_level = 1
        self.g4_verbose = False

        # visualisation (qt)
        self.visu = False
        self.visu_verbose = False
        self.visu_commands = gam.read_mac_file_to_commands('default_visu_commands.mac')

        # check volume overlap once constructed
        self.check_volumes_overlap = True

        # multithreding
        self.number_of_threads = 1

        # random engine
        self.random_engine = 'MersenneTwister'
        self.random_seed = 'auto'

    def __str__(self):
        if self.simulation.is_initialized:
            a = self.simulation.actual_random_seed
        else:
            a = ''
        s = f'Geant4 verbose  : {self.g4_verbose}, level = {self.g4_verbose_level}\n' \
            f'Visualisation   : {self.visu}, verbose level = {self.g4_verbose_level}\n' \
            f'Check overlap   : {self.check_volumes_overlap}\n' \
            f'Multi-Threading : {self.number_of_threads > 1}, threads = {self.number_of_threads}\n' \
            f'Random engine   : {self.random_engine}, seed = {self.random_seed} {a}'
        return s
