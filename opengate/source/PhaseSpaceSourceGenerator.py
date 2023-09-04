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

        if g4.IsMultithreadedApplication() and g4.G4GetThreadId() == -1:
            # do nothing for master thread
            return

        # open root file and get the first branch
        # FIXME could have an option to select the branch
        self.root_file = uproot.open(self.user_info.phsp_file)
        branches = self.root_file.keys()
        self.root_file = self.root_file[branches[0]]

        # initialize the iterator
        ui = self.user_info
        es = self.get_entry_start()
        self.iter = self.root_file.iterate(step_size=ui.batch_size, entry_start=es)

        # initialize counters
        self.num_entries = int(self.root_file.num_entries)
        self.cycle_count = 0

    def get_entry_start(self):
        ui = self.user_info
        if not g4.IsMultithreadedApplication():
            if not isinstance(ui.entry_start, numbers.Number):
                gate.fatal(f"entry_start must be a simple number is mono-thread mode")
            return self.user_info.entry_start
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
        return ui.entry_start[tid]

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
            self.iter = self.root_file.iterate(
                step_size=self.user_info.batch_size, entry_start=0
            )
            batch = next(self.iter)

        # copy to cpp
        ui = self.user_info

        # # check if the keys for particle name or PDGCode are in the root file
        if ui.PDGCode_key in batch.fields:
            source.fPDGCode = batch[ui.PDGCode_key]
        else:
            source.fPDGCode = np.zeros(len(batch), dtype=int)
        if ui.particle_name_key in batch.fields:
            source.fParticleName = batch[ui.particle_name_key]
        else:
            source.fParticleName = [""] * len(batch)

        # if neither particle name, nor PDGCode are in the root file,
        # nor the particle type was set, raise an error
        if (
            ui.particle == ""
            and ui.PDGCode_key not in batch.fields
            and ui.particle_name_key not in batch.fields
        ):
            print(
                "ERROR: PhaseSpaceSource: No particle name or PDGCode key in the root file, "
                "and no particle type was set. "
                "Please set the particle type or add the particle name or PDGCode key in the root file. Aborting."
            )
            exit(-1)

        # change position and direction of the source

        # if override_position is set to True, the position
        # supplied will be added to the root file position
        if ui.override_position:
            source.fPositionX = batch[ui.position_key_x] + ui.position.translation[0]
            source.fPositionY = batch[ui.position_key_y] + ui.position.translation[1]
            source.fPositionZ = batch[ui.position_key_z] + ui.position.translation[2]
        else:
            tid = g4.G4GetThreadId()
            source.fPositionX = batch[ui.position_key_x]
            source.fPositionY = batch[ui.position_key_y]
            source.fPositionZ = batch[ui.position_key_z]

        # direction is a rotation of the stored direction
        # if override_direction is set to True, the direction
        # in the root file will be rotated based on the supplied rotation matrix
        if ui.override_direction:
            # create point vectors
            points = np.column_stack(
                (
                    batch[ui.direction_key_x],
                    batch[ui.direction_key_y],
                    batch[ui.direction_key_z],
                )
            )
            # create rotation matrix
            r = Rotation.from_matrix(ui.position.rotation)
            # rotate vector with rotation matrix
            points = r.apply(points)
            source.fDirectionX, source.fDirectionY, source.fDirectionZ = points.T
        else:
            source.fDirectionX = batch[ui.direction_key_x]
            source.fDirectionY = batch[ui.direction_key_y]
            source.fDirectionZ = batch[ui.direction_key_z]

        # pass energy and weight
        source.fEnergy = batch[ui.energy_key]
        source.fWeight = batch[ui.weight_key]
