import threading
import uproot


class PhaseSpaceSourceGenerator:
    """
    FIXME
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.initialize_is_done = False
        self.user_info = None
        self.root_file = None

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
        # allow converting str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))
        print("read phsp and keys", self.user_info.batch_size)
        self.root_file = uproot.open(self.user_info.phsp_file)[0]
        print("open root with ", self.root_file.num_entries)

    def generator(self, source):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """
        print("generator")
        # get the info
        n = self.user_info.batch_size

        # read info from root file

        # consider the names of the output keys position/direction/energy/time/weight

        # copy to cpp
