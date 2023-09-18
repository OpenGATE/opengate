import threading
import uproot
import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation
import numpy as np
import numbers


class PhaseSpaceSourceGenerator:
    """
    Class that read phase space root file and extract position/direction/energy/weights of particles.
    Particles information will be copied to the c++ side to be used as a source
    """

    def __init__(self):
        self.current_index = None
        self.user_info = None
        self.root_file = None
        self.num_entries = 0
        self.cycle_count = 0
        # used during generation
        self.batch = None
        self.points = None
        self.w = None

    def __getstate__(self):
        self.lock = None
        return self.__dict__

    def initialize(self, user_info):
        self.user_info = user_info
        self.read_phsp_and_keys()

    def read_phsp_and_keys(self):
        # convert str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        if g4.IsMultithreadedApplication() and g4.G4GetThreadId() == -1:
            # do nothing for master thread
            return

        # open root file and get the first branch
        # FIXME could have an option to select the branch
        self.root_file = uproot.open(self.user_info.phsp_file)
        branches = self.root_file.keys()
        self.root_file = self.root_file[branches[0]]
        self.num_entries = int(self.root_file.num_entries)

        # initialize the index to start
        self.current_index = self.get_entry_start()

        # initialize counters
        self.cycle_count = 0

    def get_entry_start(self):
        ui = self.user_info
        if not g4.IsMultithreadedApplication():
            if not isinstance(ui.entry_start, numbers.Number):
                gate.fatal(f"entry_start must be a simple number is mono-thread mode")
            n = int(self.user_info.entry_start % self.num_entries)
            if self.user_info.entry_start > self.num_entries:
                gate.warning(
                    f"In source {ui.name} "
                    f"entry_start = {ui.entry_start} while "
                    f"the phsp contains {self.num_entries}. "
                    f"We consider {n} instead (modulo)"
                )
            return n
        tid = g4.G4GetThreadId()
        if tid < 0:
            # no entry start needed for master thread
            return 0
        n_threads = g4.GetNumberOfRunningWorkerThreads()
        if isinstance(ui.entry_start, numbers.Number):
            gate.fatal(f"entry_start must be a list in multi-thread mode")
        if len(ui.entry_start) != n_threads:
            gate.fatal(
                f"Error: entry_start must be a vector of length the nb of threads, "
                f"but it is {len(ui.entry_start)} instead of {n_threads}"
            )
        n = int(ui.entry_start[tid] % self.num_entries)
        if self.user_info.entry_start[tid] > self.num_entries:
            gate.warning(
                f"In source {ui.name} "
                f"entry_start = {ui.entry_start[tid]} (thread {tid}) "
                f"while the phsp contains {self.num_entries}. "
                f"We consider {n} instead (modulo)"
            )
        return n

    def generate(self, source):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """

        # read data from root tree
        ui = self.user_info
        current_batch_size = ui.batch_size
        if self.current_index + ui.batch_size > self.num_entries:
            current_batch_size = self.num_entries - self.current_index

        if ui.verbose_batch:
            print(
                f"Thread {g4.G4GetThreadId()} "
                f"generate {current_batch_size} starting {self.current_index} "
                f" (phsp as n = {self.num_entries} entries)"
            )

        self.batch = self.root_file.arrays(
            entry_start=self.current_index,
            entry_stop=self.current_index + current_batch_size,
            library="numpy",
        )
        batch = self.batch

        # update index if end of file
        self.current_index += current_batch_size
        if self.current_index >= self.num_entries:
            self.cycle_count += 1
            gate.warning(
                f"End of the phase-space {self.num_entries} elements, "
                f"restart from beginning. Cycle count = {self.cycle_count}"
            )
            self.current_index = 0

        # send to cpp
        if ui.particle == "" or ui.particle is None:
            # check if the keys for PDGCode are in the root file
            if ui.PDGCode_key in batch:
                source.SetPDGCodeBatch(batch[ui.PDGCode_key])
            else:
                gate.fatal(
                    f"PhaseSpaceSource: no PDGCode key ({ui.PDGCode_key}) "
                    f"in the phsp file and no source.particle"
                )

        # if override_position is set to True, the position
        # supplied will be added to the phsp file position
        if ui.override_position:
            x = batch[ui.position_key_x] + ui.position.translation[0]
            y = batch[ui.position_key_y] + ui.position.translation[1]
            z = batch[ui.position_key_z] + ui.position.translation[2]
            source.SetPositionXBatch(x)
            source.SetPositionYBatch(y)
            source.SetPositionZBatch(z)
        else:
            source.SetPositionXBatch(batch[ui.position_key_x])
            source.SetPositionYBatch(batch[ui.position_key_y])
            source.SetPositionZBatch(batch[ui.position_key_z])

        # direction is a rotation of the stored direction
        # if override_direction is set to True, the direction
        # in the root file will be rotated based on the supplied rotation matrix
        if ui.override_direction:
            # create point vectors
            self.points = np.column_stack(
                (
                    batch[ui.direction_key_x],
                    batch[ui.direction_key_y],
                    batch[ui.direction_key_z],
                )
            )
            # create rotation matrix
            r = Rotation.from_matrix(ui.position.rotation)
            # rotate vector with rotation matrix
            points = r.apply(self.points)
            # source.fDirectionX, source.fDirectionY, source.fDirectionZ = points.T
            source.SetDirectionXBatch(points[:, 0])
            source.SetDirectionYBatch(points[:, 1])
            source.SetDirectionZBatch(points[:, 2])
        else:
            source.SetDirectionXBatch(batch[ui.direction_key_x])
            source.SetDirectionYBatch(batch[ui.direction_key_y])
            source.SetDirectionZBatch(batch[ui.direction_key_z])

        # set energy
        source.SetEnergyBatch(batch[ui.energy_key])

        # set weight
        if ui.weight_key != "" or ui.weight_key is not None:
            if ui.weight_key in batch:
                source.SetWeightBatch(batch[ui.weight_key])
            else:
                gate.fatal(
                    f"PhaseSpaceSource: no Weight key ({ui.weight_key}) in the phsp file."
                )
        else:
            self.w = np.ones(current_batch_size)
            source.SetWeightBatch(self.w)

        return current_batch_size
