import threading
import uproot
import opengate as gate


class PhaseSpaceSourceGenerator:
    """
    Class that read phase space root file and extract position/direction/energy/weights of particles.
    Particles information will be copied to the c++ side to be used as a source
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.initialize_is_done = False
        self.user_info = None
        self.root_file = None
        self.num_entries = 0
        self.cycle_count = 0

    def __getstate__(self):
        self.lock = None
        return self.__dict__

    def initialize(self, user_info):
        with self.lock:
            if not self.initialize_is_done:
                self.user_info = user_info
                self.read_phsp_and_keys()
                self.initialize_is_done = True

    def read_phsp_and_keys(self):
        # convert str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        # open root file and get the first branch
        # FIXME could have an option to select the branch
        self.root_file = uproot.open(self.user_info.phsp_file)
        branches = self.root_file.keys()
        self.root_file = self.root_file[branches[0]]

        # initialize the iterator
        self.iter = self.root_file.iterate(step_size=self.user_info.batch_size)

        # initialize counters
        self.num_entries = int(self.root_file.num_entries)
        self.cycle_count = 0

    def generate(self, source):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """

        # read data from root tree
        try:
            batch = next(self.iter)
        except:
            self.cycle_count += 1
            gate.warning(
                f"End of the phase-space {self.num_entries} elements, "
                f"restart from beginning. Cycle count = {self.cycle_count}"
            )
            self.iter = self.root_file.iterate(step_size=self.user_info.batch_size)
            batch = next(self.iter)

        # copy to cpp
        ui = self.user_info
        source.fPositionX = batch[ui.position_key_x]
        source.fPositionY = batch[ui.position_key_y]
        source.fPositionZ = batch[ui.position_key_z]

        source.fDirectionX = batch[ui.direction_key_x]
        source.fDirectionY = batch[ui.direction_key_y]
        source.fDirectionZ = batch[ui.direction_key_z]

        source.fEnergy = batch[ui.energy_key]
        source.fWeight = batch[ui.weight_key]
