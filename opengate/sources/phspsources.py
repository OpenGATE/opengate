import uproot
import numpy as np
import numbers
from scipy.spatial.transform import Rotation
from box import Box
import sys

import opengate_core as g4
from ..exception import fatal, warning
from .generic import SourceBase
from ..base import process_cls


class PhaseSpaceSourceGenerator:
    """
    Class that read phase space root file and extract position/direction/energy/weights of particles.
    Particles information will be copied to the c++ side to be used as a source
    """

    def __init__(self, tid):
        self.phsp_source = None
        self.tid = tid
        self.root_file = None
        self.num_entries = 0
        self.cycle_count = 0
        self.cycle_changed_flag = False
        # used during generation
        self.batch = None
        self.points = None
        self.current_index = 0
        self.w = None

    def initialize(self, phsp_source):
        self.phsp_source = phsp_source
        self.name = phsp_source.name
        # set the keys and entry start
        self.read_phsp_and_keys()

    def read_phsp_and_keys(self):
        # convert str like 1e5 to int
        self.phsp_source.batch_size = int(self.phsp_source.batch_size)
        if self.phsp_source.batch_size < 1:
            fatal("PhaseSpaceSourceGenerator: Batch size should be > 0")

        if g4.IsMultithreadedApplication() and g4.G4GetThreadId() == -1:
            # do nothing for master thread
            return

        # open root file and get the first branch
        # FIXME could have an option to select the branch
        self.root_file = uproot.open(self.phsp_source.phsp_file)
        branches = self.root_file.keys()
        if len(branches) > 0:
            self.root_file = self.root_file[branches[0]]
        else:
            fatal(
                f"PhaseSpaceSourceGenerator: No usable branches in the root file {self.phsp_source.phsp_file}. Aborting."
            )
            sys.exit()

        self.num_entries = int(self.root_file.num_entries)

        # initialize the index to start
        tid = g4.G4GetThreadId()
        self.current_index = self.get_entry_start(self.phsp_source.entry_start)

        # initialize counters
        self.cycle_count = 0

    def get_entry_start(self, entry_start):
        if not g4.IsMultithreadedApplication():
            if not isinstance(entry_start, numbers.Number):
                fatal("entry_start must be a simple number is mono-thread mode")
            n = int(entry_start % self.num_entries)
            if entry_start > self.num_entries:
                warning(
                    f"In source {self.name} "
                    f"entry_start = {entry_start} while "
                    f"the phsp contains {self.num_entries}. "
                    f"We consider {n} instead (modulo)"
                )
            return n
        tid = g4.G4GetThreadId()

        if tid < 0:
            # no entry start needed for master thread
            return 0
        n_threads = g4.GetNumberOfRunningWorkerThreads()
        if isinstance(entry_start, numbers.Number):
            fatal(f"entry_start must be a list in multi-thread mode")
        if len(entry_start) != n_threads:
            fatal(
                f"Error: entry_start must be a vector of length the nb of threads, "
                f"but it is {len(entry_start)} instead of {n_threads}"
            )
        n = int(entry_start[self.tid] % self.num_entries)
        if entry_start[tid] > self.num_entries:
            warning(
                f"In source {self.name} "
                f"entry_start = {entry_start} (thread {tid}) "
                f"while the phsp contains {self.num_entries}. "
                f"We consider {n} instead (modulo)"
            )
        return n

    def generate(self, source, pid):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """

        # warn phsp is recycled
        if self.cycle_changed_flag:
            warning(
                f"End of the phase-space {self.num_entries} elements, "
                f"restart from beginning. Cycle count = {self.cycle_count}"
            )
            self.cycle_changed_flag = False
            self.current_index = 0

        # read data from root tree
        current_batch_size = source.batch_size
        if self.current_index + source.batch_size >= self.num_entries:
            current_batch_size = self.num_entries - self.current_index
            self.cycle_count += 1
            self.cycle_changed_flag = True

        if source.verbose_batch:
            print(
                f"Thread {g4.G4GetThreadId()} "
                f"generate {current_batch_size} starting {self.current_index} "
                f" (phsp as n = {self.num_entries} entries)"
            )

        # read a batch of particles in the phsp (keep the reference)
        self.batch = self.root_file.arrays(
            entry_start=self.current_index,
            entry_stop=self.current_index + current_batch_size,
            library="numpy",
        )
        batch = self.batch
        self.current_index += current_batch_size

        # ensure encoding is float32
        for key in batch:
            # Convert to float32 if the array contains floating-point values
            if np.issubdtype(batch[key].dtype, np.floating):
                batch[key] = batch[key].astype(np.float32)
            else:
                if np.issubdtype(batch[key].dtype, np.integer):
                    batch[key] = batch[key].astype(np.int32)

        # set particle type
        if source.particle == "" or source.particle is None:
            # check if the keys for PDGCode are in the root file
            if source.PDGCode_key not in batch:
                fatal(
                    f"PhaseSpaceSource: no PDGCode key ({source.PDGCode_key}) "
                    f"in the phsp file and no source.particle"
                )

        # if translate_position is set to True, the position
        # supplied will be added to the phsp file position
        if source.translate_position:
            batch[source.position_key_x] += float(source.position.translation[0])
            batch[source.position_key_y] += float(source.position.translation[1])
            batch[source.position_key_z] += float(source.position.translation[2])

        # direction is a rotation of the stored direction
        # if rotate_direction is set to True, the direction
        # in the root file will be rotated based on the supplied rotation matrix
        if source.rotate_direction:
            # create point vectors
            self.points = np.column_stack(
                (
                    batch[source.direction_key_x],
                    batch[source.direction_key_y],
                    batch[source.direction_key_z],
                )
            )
            # create rotation matrix
            r = Rotation.from_matrix(source.position.rotation)
            if source.verbose:
                print("Rotation matrix: ", r.as_matrix())
            # rotate vector with rotation matrix
            points = r.apply(self.points)
            # source.fDirectionX, source.fDirectionY, source.fDirectionZ = points.T
            batch[source.direction_key_x] = points[:, 0].astype(np.float32)
            batch[source.direction_key_y] = points[:, 1].astype(np.float32)
            batch[source.direction_key_z] = points[:, 2].astype(np.float32)

        # set weight
        if source.weight_key != "" and source.weight_key is not None:
            if source.weight_key not in batch:
                fatal(
                    f"PhaseSpaceSource: no Weight key ({source.weight_key}) in the phsp file."
                )
        else:
            self.w = np.ones(current_batch_size, dtype=np.float32)
            batch[source.weight_key] = self.w.astype(np.float32)

        # send to cpp
        # set position
        source.SetPositionXBatch(batch[source.position_key_x])
        source.SetPositionYBatch(batch[source.position_key_y])
        source.SetPositionZBatch(batch[source.position_key_z])

        # set direction
        source.SetDirectionXBatch(batch[source.direction_key_x])
        source.SetDirectionYBatch(batch[source.direction_key_y])
        source.SetDirectionZBatch(batch[source.direction_key_z])

        # set energy
        source.SetEnergyBatch(batch[source.energy_key])

        # set PDGCode
        if source.PDGCode_key in batch:
            source.SetPDGCodeBatch(batch[source.PDGCode_key])
        # set weight
        source.SetWeightBatch(batch[source.weight_key])

        if source.verbose:
            print("PhaseSpaceSourceGenerator: batch generated: ")
            print("particle name: ", source.particle)
            if source.PDGCode_key in batch:
                print("source.fPDGCode: ", batch[source.PDGCode_key])
            print("source.fEnergy: ", batch[source.energy_key])
            print("source.fWeight: ", batch[source.weight_key])
            print("source.fPositionX: ", batch[source.position_key_x])
            print("source.fPositionY: ", batch[source.position_key_y])
            print("source.fPositionZ: ", batch[source.position_key_z])
            print("source.fDirectionX: ", batch[source.direction_key_x])
            print("source.fDirectionY: ", batch[source.direction_key_y])
            print("source.fDirectionZ: ", batch[source.direction_key_z])
            print("source.fEnergy dtype: ", batch[source.energy_key].dtype)

        return current_batch_size


class PhaseSpaceSource(SourceBase, g4.GatePhaseSpaceSource):
    """
    Source of particles from a (root) phase space.
    Read position + direction + energy + weight from the root and use them as event.

    If "global flag" is True, the position/direction are global, ie in the world coordinate system.
    If it is False, it uses the coordinate system of the volume it is attached to.

    The Time in the phsp is not implemented (yet)
    """

    # hints for IDE
    phsp_file: str
    entry_start: int
    particle: str
    global_flag: bool
    isotropic_momentum: bool
    translate_position: bool
    rotate_direction: bool
    batch_size: int
    position_key: str
    position_key_x: str
    position_key_y: str
    position_key_z: str
    direction_key: str
    direction_key_x: str
    direction_key_y: str
    direction_key_z: str
    energy_key: str
    weight_key: str
    PDGCode_key: str
    generate_until_next_primary: bool
    primary_lower_energy_threshold: float
    primary_PDGCode: int
    verbose: bool

    user_info_defaults = {
        "phsp_file": (
            None,
            {"doc": "Filename of the phase-space file (root). This is required"},
        ),
        "entry_start": (
            None,
            {
                "doc": "Starting particle in the phase-space (for MT, provide a list of entries, one for each thread)"
            },
        ),
        "particle": ("", {"doc": "FIXME"}),
        "global_flag": (
            False,
            {
                "doc": "If true, the positions of the generated particles in the phase-space "
                "are in the world coordinate system. If false, they are relative to the volume"
                "this source is attached to",
            },
        ),
        "isotropic_direction": (
            False,
            {
                "doc": "If true, It enables to generate a particle with a position energy and weight "
                "according to the provided phase but with an isotropic momentum.",
            },
        ),
        "translate_position": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "rotate_direction": (
            False,
            {
                "doc": "FIXME",
            },
        ),
        "batch_size": (
            10000,
            {
                "doc": "Batch size to read the phsp",
            },
        ),
        "position_key": (
            "PrePositionLocal",
            {
                "doc": "Key in the phsp that contain the position of the particle. Automatically set the"
                " position_key_x, position_key_y, position_key_z keys by adding _X _Y _Z",
                # "setter_hook": _setter_hook_phsp_source_3d_keys,
            },
        ),
        "position_key_x": (
            None,
            {
                "doc": "Key in the phsp that contain the position X of the particle",
            },
        ),
        "position_key_y": (
            None,
            {
                "doc": "Key in the phsp that contain the position Y of the particle",
            },
        ),
        "position_key_z": (
            None,
            {
                "doc": "Key in the phsp that contain the position Z of the particle",
            },
        ),
        "position": (
            Box(
                {"translation": [0, 0, 0], "rotation": Rotation.identity().as_matrix()}
            ),
            {
                "doc": "Default position+rotation if it is not read in the phsp",
            },
        ),
        "direction_key": (
            "PreDirectionLocal",
            {
                "doc": "Key in the phsp that contain the direction of the particle. Automatically set the"
                " direction_key_x, direction_key_y, direction_key_z keys by adding _X _Y _Z",
                # "setter_hook": _setter_hook_phsp_source_3d_keys,
            },
        ),
        "direction_key_x": (
            None,
            {
                "doc": "Key in the phsp that contain the direction X of the particle",
            },
        ),
        "direction_key_y": (
            None,
            {
                "doc": "Key in the phsp that contain the direction Y of the particle",
            },
        ),
        "direction_key_z": (
            None,
            {
                "doc": "Key in the phsp that contain the direction Z of the particle",
            },
        ),
        "energy_key": (
            "KineticEnergy",
            {
                "doc": "Key in the phsp that contain the energy of the particle",
            },
        ),
        "weight_key": (
            "Weight",
            {
                "doc": "Key in the phsp that contain the weight of the particle",
            },
        ),
        "PDGCode_key": (
            "PDGCode",
            {
                "doc": "Key in the phsp that contains the PDGCode of the particle (particle type) "
                "see https://pdg.lbl.gov/2007/reviews/montecarlorpp.pdf",
            },
        ),
        "generate_until_next_primary": (
            False,
            {
                "doc": "FIXME ",
            },
        ),
        "primary_lower_energy_threshold": (
            0,
            {
                "doc": "FIXME ",
            },
        ),
        "primary_PDGCode": (
            0,
            {
                "doc": "FIXME ",
            },
        ),
        "verbose": (
            False,
            {
                "doc": "FIXME ",
            },
        ),
        "verbose_batch": (
            False,
            {
                "doc": "FIXME ",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()
        # there will be one particle generator per thread
        self.particle_generators = {}
        # number of entries in the phsp root file
        self.num_entries = None

    def __initcpp__(self):
        g4.GatePhaseSpaceSource.__init__(self)

    def __getstate__(self):
        # the particle generator cannot (?) being pickled
        # we convert in a dict with the cycle count values
        all_pg = self.particle_generators
        self.particle_generators = {}
        for k, pg in all_pg.items():
            self.particle_generators[k] = Box({"cycle_count": pg.cycle_count})
        state_dict = super().__getstate__()
        return state_dict

    def initialize(self, run_timing_intervals):
        # create a generator for each thread
        tid = g4.G4GetThreadId()
        self.particle_generators[tid] = PhaseSpaceSourceGenerator(tid)

        # initialize source
        SourceBase.initialize(self, run_timing_intervals)

        # check user info
        if self.position_key_x is None:
            self.position_key_x = f"{self.position_key}_X"
        if self.position_key_y is None:
            self.position_key_y = f"{self.position_key}_Y"
        if self.position_key_z is None:
            self.position_key_z = f"{self.position_key}_Z"

        if self.direction_key_x is None:
            self.direction_key_x = f"{self.direction_key}_X"
        if self.direction_key_y is None:
            self.direction_key_y = f"{self.direction_key}_Y"
        if self.direction_key_z is None:
            self.direction_key_z = f"{self.direction_key}_Z"

        # check if the source should generate particles until the second one
        # which is identified as primary by name, PDGCode and above a threshold
        if self.generate_until_next_primary:
            if self.primary_PDGCode == 0:
                fatal(
                    "PhaseSpaceSource: generate_until_next_primary is True but no primary particle is defined"
                )
            if self.primary_lower_energy_threshold <= 0:
                fatal(
                    "PhaseSpaceSource: generate_until_next_primary is True but no "
                    "primary_lower_energy_threshold is defined"
                )

        # if not set, initialize the entry_start to 0 or to a list for multithreading
        if self.entry_start is None:
            if not g4.IsMultithreadedApplication():
                self.entry_start = 0
            else:
                # create an entry_start array with the correct number of start entries
                # all entries are spaced by the number of particles/thread
                # FIXME: check this line. I corrected it because it seemed like a typo (NK)
                n_threads = self.simulation.number_of_threads
                # n_threads = self.simulation.phsp_source.number_of_threads
                step = np.ceil(self.n / n_threads) + 1  # Specify the increment value
                self.entry_start = [i * step for i in range(n_threads)]

        # initialize the generator (read the phsp file)
        self.particle_generators[tid].initialize(self)

        # keep a copy of the number of entries
        self.num_entries = self.particle_generators[tid].num_entries

        # set the function pointer to the cpp side
        self.SetGeneratorFunction(self.particle_generators[tid].generate)

    @property
    def cycle_count(self):
        if not g4.IsMultithreadedApplication():
            tid = g4.G4GetThreadId()
            return self.particle_generators[tid].cycle_count
        else:
            s = " ".join(
                str(self.particle_generators[tid].cycle_count)
                for tid in self.particle_generators.keys()
            )
            return s


process_cls(PhaseSpaceSource)
