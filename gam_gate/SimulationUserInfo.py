import gam_gate as gam
import gam_g4 as g4


class SimulationUserInfo:
    """
        This class is a simple structure that contains all user general options of a simulation.
    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # gam (pre-run) verbose
        # A number or gam.NONE or gam.INFO or gam.DEBUG
        self._verbose_level = gam.INFO
        gam.log.setLevel(self._verbose_level)

        # gam verbose during running
        self.running_verbose_level = 0

        # Geant4 verbose
        self.g4_verbose_level = 1
        self.g4_verbose = False

        # visualisation (qt)
        self.visu = False
        self.visu_verbose = False
        self.visu_commands = gam.read_mac_file_to_commands('default_visu_commands.mac')

        # check volume overlap once constructed
        self.check_volumes_overlap = True

        # multi-threading
        self.number_of_threads = 1
        self.force_multithread_mode = False

        # random engine
        # MixMaxRng seems recommended for MultiThread
        self.random_engine = 'MixMaxRng'  # 'MersenneTwister'
        self.random_seed = 'auto'

    @property
    def verbose_level(self):
        return self._verbose_level

    @verbose_level.setter
    def verbose_level(self, value):
        gam.log.setLevel(value)
        self._verbose_level = value

    def __del__(self):
        pass

    def __str__(self):
        if self.simulation.is_initialized:
            a = self.simulation.actual_random_seed
        else:
            a = ''
        if self.number_of_threads == 1 and not self.force_multithread_mode:
            g = g4.GamInfo.get_G4MULTITHREADED()
            t = 'no'
            if g:
                t += ' (but available: G4 was compiled with MT)'
            else:
                t += ' (not available, G4 was not compiled with MT)'
        else:
            t = f'{self.number_of_threads} threads'
        s = f'Verbose        : {self.verbose_level}\n' \
            f'Running verbose: {self.running_verbose_level}\n' \
            f'Geant4 verbose : {self.g4_verbose}, level = {self.g4_verbose_level}\n' \
            f'Visualisation  : {self.visu}, verbose level = {self.g4_verbose_level}\n' \
            f'Check overlap  : {self.check_volumes_overlap}\n' \
            f'Multithreading : {t}\n' \
            f'Random engine  : {self.random_engine}, seed = {self.random_seed} {a}'
        return s
