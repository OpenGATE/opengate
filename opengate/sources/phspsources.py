import uproot
import numpy as np
import numbers
from scipy.spatial.transform import Rotation
from box import Box

import opengate_core
from ..exception import fatal, warning
from .generic import SourceBase


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
        ## FIXME
        return self.__dict__

    def initialize(self, user_info):
        self.user_info = user_info
        self.read_phsp_and_keys()

    def read_phsp_and_keys(self):
        # convert str like 1e5 to int
        self.user_info.batch_size = int(self.user_info.batch_size)
        if self.user_info.batch_size < 1:
            fatal("PhaseSpaceSourceGenerator: Batch size should be > 0")

        if (
            opengate_core.IsMultithreadedApplication()
            and opengate_core.G4GetThreadId() == -1
        ):
            # do nothing for master thread
            return

        # open root file and get the first branch
        # FIXME could have an option to select the branch
        self.root_file = uproot.open(self.user_info.phsp_file)
        branches = self.root_file.keys()
        if len(branches) > 0:
            self.root_file = self.root_file[branches[0]]
        else:
            fatal(
                f"PhaseSpaceSourceGenerator: No usable branches in the root file {self.user_info.phsp_file}. Aborting."
            )
            exit()

        self.num_entries = int(self.root_file.num_entries)

        # initialize the index to start
        self.current_index = self.get_entry_start()

        # initialize counters
        self.cycle_count = 0

    def get_entry_start(self):
        ui = self.user_info
        if not opengate_core.IsMultithreadedApplication():
            if not isinstance(ui.entry_start, numbers.Number):
                fatal(f"entry_start must be a simple number is mono-thread mode")
            n = int(self.user_info.entry_start % self.num_entries)
            if self.user_info.entry_start > self.num_entries:
                warning(
                    f"In source {ui.name} "
                    f"entry_start = {ui.entry_start} while "
                    f"the phsp contains {self.num_entries}. "
                    f"We consider {n} instead (modulo)"
                )
            return n
        tid = opengate_core.G4GetThreadId()
        if tid < 0:
            # no entry start needed for master thread
            return 0
        n_threads = opengate_core.GetNumberOfRunningWorkerThreads()
        if isinstance(ui.entry_start, numbers.Number):
            fatal(f"entry_start must be a list in multi-thread mode")
        if len(ui.entry_start) != n_threads:
            fatal(
                f"Error: entry_start must be a vector of length the nb of threads, "
                f"but it is {len(ui.entry_start)} instead of {n_threads}"
            )
        n = int(ui.entry_start[tid] % self.num_entries)
        if self.user_info.entry_start[tid] > self.num_entries:
            warning(
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
                f"Thread {opengate_core.G4GetThreadId()} "
                f"generate {current_batch_size} starting {self.current_index} "
                f" (phsp as n = {self.num_entries} entries)"
            )

        self.batch = self.root_file.arrays(
            entry_start=self.current_index,
            entry_stop=self.current_index + current_batch_size,
            library="numpy",
        )

        batch = self.batch
        # ensure encoding is float32
        for key in batch:
            # Convert to float32 if the array contains floating-point values
            if np.issubdtype(batch[key].dtype, np.floating):
                batch[key] = batch[key].astype(np.float32)
            else:
                if np.issubdtype(batch[key].dtype, np.integer):
                    batch[key] = batch[key].astype(np.int32)

        # update index if end of file
        self.current_index += current_batch_size
        if self.current_index >= self.num_entries:
            self.cycle_count += 1
            warning(
                f"End of the phase-space {self.num_entries} elements, "
                f"restart from beginning. Cycle count = {self.cycle_count}"
            )
            self.current_index = 0

        # set particle type
        if ui.particle == "" or ui.particle is None:
            # check if the keys for PDGCode are in the root file
            if ui.PDGCode_key not in batch:
                fatal(
                    f"PhaseSpaceSource: no PDGCode key ({ui.PDGCode_key}) "
                    f"in the phsp file and no source.particle"
                )

        # if translate_position is set to True, the position
        # supplied will be added to the phsp file position
        if ui.translate_position:
            batch[ui.position_key_x] += float(ui.position.translation[0])
            batch[ui.position_key_y] += float(ui.position.translation[1])
            batch[ui.position_key_z] += float(ui.position.translation[2])

        # direction is a rotation of the stored direction
        # if rotate_direction is set to True, the direction
        # in the root file will be rotated based on the supplied rotation matrix
        if ui.rotate_direction:
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
            if ui.verbose:
                print("Rotation matrix: ", r.as_matrix())
            # rotate vector with rotation matrix
            points = r.apply(self.points)
            # source.fDirectionX, source.fDirectionY, source.fDirectionZ = points.T
            batch[ui.direction_key_x] = points[:, 0].astype(np.float32)
            batch[ui.direction_key_y] = points[:, 1].astype(np.float32)
            batch[ui.direction_key_z] = points[:, 2].astype(np.float32)

        # set weight
        if ui.weight_key != "" and ui.weight_key is not None:
            if ui.weight_key not in batch:
                fatal(
                    f"PhaseSpaceSource: no Weight key ({ui.weight_key}) in the phsp file."
                )
        else:
            self.w = np.ones(current_batch_size, dtype=np.float32)
            batch[ui.weight_key] = self.w.astype(np.float32)

        # send to cpp
        # set position
        source.SetPositionXBatch(batch[ui.position_key_x])
        source.SetPositionYBatch(batch[ui.position_key_y])
        source.SetPositionZBatch(batch[ui.position_key_z])
        # set direction
        source.SetDirectionXBatch(batch[ui.direction_key_x])
        source.SetDirectionYBatch(batch[ui.direction_key_y])
        source.SetDirectionZBatch(batch[ui.direction_key_z])
        # set energy
        source.SetEnergyBatch(batch[ui.energy_key])
        # set PDGCode
        if ui.PDGCode_key in batch:
            source.SetPDGCodeBatch(batch[ui.PDGCode_key])
        # set weight
        source.SetWeightBatch(batch[ui.weight_key])

        if ui.verbose:
            print("PhaseSpaceSourceGenerator: batch generated: ")
            print("particle name: ", ui.particle)
            if ui.PDGCode_key in batch:
                print("source.fPDGCode: ", batch[ui.PDGCode_key])
            print("source.fEnergy: ", batch[ui.energy_key])
            print("source.fWeight: ", batch[ui.weight_key])
            print("source.fPositionX: ", batch[ui.position_key_x])
            print("source.fPositionY: ", batch[ui.position_key_y])
            print("source.fPositionZ: ", batch[ui.position_key_z])
            print("source.fDirectionX: ", batch[ui.direction_key_x])
            print("source.fDirectionY: ", batch[ui.direction_key_y])
            print("source.fDirectionZ: ", batch[ui.direction_key_z])
            print("source.fEnergy dtype: ", batch[ui.energy_key].dtype)

        return current_batch_size


class PhaseSpaceSource(SourceBase):
    """
    Source of particles from a (root) phase space.
    Read position + direction + energy + weight from the root and use them as event.

    if global flag is True, the position/direction are global, not
    in the coordinate system of the mother volume.
    if the global flag is False, the position/direction are relative
    to the mother volume

    - Timing is not used (yet)
    - NOT ready for multithread (yet)
    - type of particle not read in the phase space but set by user

    """

    type_name = "PhaseSpaceSource"

    @staticmethod
    def set_default_user_info(user_info):
        SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.phsp_file = None
        user_info.n = 0
        user_info.activity = 0
        user_info.half_life = -1  # negative value is not half_life
        user_info.particle = ""  # FIXME later as key
        user_info.entry_start = None
        # if a particle name is supplied, the particle type is set to it
        # otherwise, information from the phase space is used

        # if global flag is True, the position/direction are global, not
        # in the coordinate system of the mother volume.
        # if the global flag is False, the position/direction are relative
        # to the mother volume
        user_info.global_flag = False
        user_info.batch_size = 10000
        # branch name in the phsp file
        user_info.position_key = "PrePositionLocal"
        user_info.position_key_x = None
        user_info.position_key_y = None
        user_info.position_key_z = None
        user_info.direction_key = "PreDirectionLocal"
        user_info.direction_key_x = None
        user_info.direction_key_y = None
        user_info.direction_key_z = None
        user_info.energy_key = "KineticEnergy"
        user_info.weight_key = "Weight"
        user_info.PDGCode_key = "PDGCode"
        # change position and direction of the source
        # position is relative to the stored coordinates
        # direction is a rotation of the stored direction
        user_info.translate_position = False
        user_info.rotate_direction = False
        user_info.position = Box()
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        user_info.generate_until_next_primary = False
        user_info.primary_lower_energy_threshold = 0
        user_info.primary_PDGCode = 0
        user_info.verbose = False
        # user_info.time_key = None # FIXME TODO later
        # for debug
        user_info.verbose_batch = False
        user_info.verbose = False

    def create_g4_source(self):
        return opengate_core.GatePhaseSpaceSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.particle_generator = PhaseSpaceSourceGenerator()
        # FIXME workaround for ./test019_linac_phsp_source.py
        self.user_info.particle_generator = self.particle_generator

    def initialize(self, run_timing_intervals):
        # initialize the mother class generic source

        SourceBase.initialize(self, run_timing_intervals)

        # check user info
        ui = self.user_info
        if ui.position_key_x is None:
            ui.position_key_x = f"{ui.position_key}_X"
        if ui.position_key_y is None:
            ui.position_key_y = f"{ui.position_key}_Y"
        if ui.position_key_z is None:
            ui.position_key_z = f"{ui.position_key}_Z"
        if ui.direction_key_x is None:
            ui.direction_key_x = f"{ui.direction_key}_X"
        if ui.direction_key_y is None:
            ui.direction_key_y = f"{ui.direction_key}_Y"
        if ui.direction_key_z is None:
            ui.direction_key_z = f"{ui.direction_key}_Z"

        # check if the source should generate particles until the second one
        # which is identified as primary by name, PDGCode and above a threshold
        if ui.generate_until_next_primary:
            if ui.primary_PDGCode == 0:
                fatal(
                    f"PhaseSpaceSource: generate_until_next_primary is True but no primary particle is defined"
                )
            if ui.primary_lower_energy_threshold <= 0:
                fatal(
                    f"PhaseSpaceSource: generate_until_next_primary is True but no primary_lower_energy_threshold is defined"
                )

        # if not set, initialize the entry_start to 0 or to a list for multithreading
        if ui.entry_start is None:
            if not opengate_core.IsMultithreadedApplication():
                ui.entry_start = 0
            else:
                # create an entry_start array with the correct number of start entries
                # all entries are spaced by the number of particles/thread
                n_threads = self.simulation.user_info.number_of_threads
                step = np.ceil(ui.n / n_threads) + 1  # Specify the increment value
                ui.entry_start = [i * step for i in range(n_threads)]

        # initialize the generator (read the phsp file)
        self.particle_generator.initialize(self.user_info)

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(self.particle_generator.generate)
