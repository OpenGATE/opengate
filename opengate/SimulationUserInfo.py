import opengate as gate
import opengate_core as g4


class SimulationUserInfo:
    """
    This class is a simple structure that contains all user general options of a simulation.
    """

    def __init__(self, simulation):
        # keep pointer to ref
        self.simulation = simulation

        # gate (pre-run) verbose
        # A number or gate.NONE or gate.INFO or gate.DEBUG
        self._verbose_level = gate.INFO
        gate.log.setLevel(self._verbose_level)

        # gate verbose during running
        self.running_verbose_level = 0

        # Geant4 verbose
        # For an unknown reason, when verbose_level == 0, there are some
        # additional print after the G4RunManager destructor. So we default at 1
        self.g4_verbose_level = 1
        self.g4_verbose = False

        # visualisation (qt|vrml)
        self.visu = False
        self.visu_type = "qt"  # choice: "qt" or "vrml"
        self.visu_verbose = False
        self.visu_commands = gate.read_mac_file_to_commands("default_visu_commands.mac")
        self.visu_commands_vrml = gate.read_mac_file_to_commands(
            "default_visu_commands_vrml.mac"
        )

        # check volume overlap once constructed
        self.check_volumes_overlap = True

        # multi-threading
        self.number_of_threads = 1
        self.force_multithread_mode = False

        # random engine
        # MixMaxRng seems recommended for MultiThread
        self.random_engine = "MixMaxRng"  # 'MersenneTwister'
        self.random_seed = "auto"

    @property
    def verbose_level(self):
        return self._verbose_level

    @verbose_level.setter
    def verbose_level(self, value):
        gate.log.setLevel(value)
        self._verbose_level = value

    def __del__(self):
        pass

    def __str__(self):
        if self.number_of_threads == 1 and not self.force_multithread_mode:
            g = g4.GateInfo.get_G4MULTITHREADED()
            t = "no"
            if g:
                t += " (but available: G4 was compiled with MT)"
            else:
                t += " (not available, G4 was not compiled with MT)"
        else:
            t = f"{self.number_of_threads} threads"
        s = (
            f"Verbose         : {self.verbose_level}\n"
            f"Running verbose : {self.running_verbose_level}\n"
            f"Geant4 verbose  : {self.g4_verbose}, level = {self.g4_verbose_level}\n"
            f"Visualisation   : {self.visu}, verbose level = {self.g4_verbose_level}\n"
            f"Visutype        : {self.visu_type}\n"
            f"Check overlap   : {self.check_volumes_overlap}\n"
            f"Multithreading  : {t}\n"
            f"Random engine   : {self.random_engine}, seed = {self.random_seed}"
        )
        return s
