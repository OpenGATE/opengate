import sys
import time
import scipy
import numpy as np
import threading
from box import Box
import itk
import bisect
import opengate_core
from ..exception import fatal
from .generic import GenericSource
from ..image import get_info_from_image
from ..image import compute_image_3D_CDF
from .generic import generate_isotropic_directions
from scipy.spatial.transform import Rotation
from ..utility import LazyModuleLoader

#
torch = LazyModuleLoader("torch")
gaga = LazyModuleLoader("gaga_phsp")


class VoxelizedSourcePDFSampler:
    """
    This is an alternative to GateSPSVoxelsPosDistribution (c++)
    It is needed because the cond voxel source is used on python side.

    There are two versions, version 2 is much slower (do not use)
    """

    def __init__(self, itk_image, version=1):
        self.image = itk_image
        self.version = version
        # get image in np array
        self.imga = itk.array_view_from_image(itk_image)
        imga = self.imga

        # image sizes
        lx = self.imga.shape[0]
        ly = self.imga.shape[1]
        lz = self.imga.shape[2]
        m = lx * ly * lz

        # normalized pdf
        pdf = imga.ravel(order="F")
        self.pdf = pdf / pdf.sum()

        # create grid of indices
        [x_grid, y_grid, z_grid] = np.meshgrid(
            np.arange(lx), np.arange(ly), np.arange(lz), indexing="ij"
        )

        # list of indices
        self.xi, self.yi, self.zi = (
            x_grid.ravel(order="F"),
            y_grid.ravel(order="F"),
            z_grid.ravel(order="F"),
        )

        # 1D indices
        self.linear_indices = np.arange(int(m))

        if version == 2:
            self.init_cdf()

        if version == 3:
            self.init_cdf()

        # ------------------------------------------
        # Below = NOT WORKING, DO NOT USE
        # create grid of indices in physical space
        """img_info = gate.get_info_from_image(self.image)
        sp = img_info.spacing
        hsp = sp / 2
        s = img_info.size * sp
        [px_grid, py_grid, pz_grid] = np.meshgrid(
            np.linspace(hsp[0], s[0] - hsp[0], lx),
            np.linspace(hsp[1], s[1] - hsp[1], lx),
            np.linspace(hsp[2], s[2] - hsp[2], lz),
            indexing='ij',
        )
        # list of indices
        self.pxi, self.pyi, self.pzi = (
            px_grid.ravel(order='F'),
            py_grid.ravel(order='F'),
            pz_grid.ravel(order='F'),
        )
        """
        # ------------------------------------------

    def init_cdf(self):
        self.cdf_x, self.cdf_y, self.cdf_z = compute_image_3D_CDF(self.image)
        self.cdf_x = np.array(self.cdf_x)
        self.cdf_y = np.array(self.cdf_y)
        self.cdf_z = np.array(self.cdf_z)
        self.cdf_init = True

    def searchsorted2d(self, a, b):
        # https://stackoverflow.com/questions/56471109/how-to-vectorize-with-numpy-searchsorted-in-a-2d-array
        # Inputs : a is (m,n) 2D array and b is (m,) 1D array.
        # Finds np.searchsorted(a[i], b[i])) in a vectorized way by
        # scaling/offsetting both inputs and then using searchsorted

        # Get scaling offset and then scale inputs
        s = np.r_[0, (np.maximum(a.max(1) - a.min(1) + 1, b) + 1).cumsum()[:-1]]
        a_scaled = (a + s[:, None]).ravel()
        b_scaled = b + s

        # Use searchsorted on scaled ones and then subtract offsets
        return np.searchsorted(a_scaled, b_scaled) - np.arange(len(s)) * a.shape[1]

    def sample_indices_slower(self, n, rs=np.random):
        """
        This version seems slower than the other version with np random choice
        """
        # Z (here, search sorted is faster than bisect+loop)
        uz = rs.uniform(0, 1, size=n)
        # i = [bisect.bisect_left(self.cdf_z, uz[t], lo=0, hi=lz) for t in range(n)]
        i = np.searchsorted(self.cdf_z, uz, side="left")

        # Y, knowing Z
        # https://stackoverflow.com/questions/56471109/how-to-vectorize-with-numpy-searchsorted-in-a-2d-array
        ly = self.imga.shape[1]
        uy = rs.uniform(0, 1, size=n)
        j = [bisect.bisect_left(self.cdf_y[i[t]], uy[t], lo=0, hi=ly) for t in range(n)]

        # (here search sorted is not faster, we keep bisect)
        # slower:
        # cdfyi = np.take(self.cdf_y, i, axis=0)
        # j = self.searchsorted2d(cdfyi, uy)

        # X
        lx = self.imga.shape[2]
        ux = rs.uniform(0, 1, size=n)
        k = [
            bisect.bisect_left(self.cdf_x[i[t]][j[t]], ux[t], lo=0, hi=lx)
            for t in range(n)
        ]

        return i, j, k

    def samples_g4(self, n):
        # to compare with cpp version
        sps = opengate_core.GateSPSVoxelsPosDistribution()
        sps.SetCumulativeDistributionFunction(self.cdf_z, self.cdf_y, self.cdf_x)
        p = np.array([sps.VGenerateOneDebug() for a in range(n)])
        return p[:, 2], p[:, 1], p[:, 0]

    def sample_indices(self, n, rs=np.random):
        indices = rs.choice(self.linear_indices, size=n, replace=True, p=self.pdf)
        i = self.xi[indices]
        j = self.yi[indices]
        k = self.zi[indices]
        return i, j, k

    def sample_indices_phys(self, n, rs=np.random):
        # TODO (not used yet)
        indices = rs.choice(self.linear_indices, size=n, replace=True, p=self.pdf)
        i = self.pxi[indices]
        j = self.pyi[indices]
        k = self.pzi[indices]
        return i, j, k


class VoxelizedSourceConditionGenerator:
    def __init__(
        self, activity_source_filename, rs=np.random, use_activity_origin=False
    ):
        self.activity_source_filename = str(activity_source_filename)
        # options
        self.compute_directions = False
        self.use_activity_origin = use_activity_origin
        self.translation = [0, 0, 0]
        self.rotation = Rotation.identity().as_matrix()
        # variables
        self.image = None
        self.cdf_x = self.cdf_y = self.cdf_z = None
        self.rs = rs
        self.source_img_info = None
        self.sampler = None
        self.points_offset = None
        # init
        self.is_initialized = False

    def initialize_source(self):
        # FIXME warning, this is call in the same thread but several time (???)
        if self.image is None:
            self.image = itk.imread(self.activity_source_filename)
        self.source_img_info = get_info_from_image(self.image)
        if self.sampler is None:
            self.sampler = VoxelizedSourcePDFSampler(self.image)
        self.rs = np.random
        # we set the points in the g4 coord system (according to the center of the image)
        # or according to the activity source image origin
        if self.use_activity_origin is True:
            self.points_offset = self.source_img_info.origin
        else:
            hs = self.source_img_info.spacing / 2.0
            self.points_offset = -hs * self.source_img_info.size + hs
        self.is_initialized = True

    def generate_condition(self, n):
        if self.is_initialized is False:
            self.initialize_source()

        # i j k is in np array order = z y x
        # but img_info is in the order x y z
        i, j, k = self.sampler.sample_indices(n, self.rs)

        # half pixel size
        hs = self.source_img_info.spacing / 2.0

        # sample within the voxel
        rx = self.rs.uniform(-hs[0], hs[0], size=n)
        ry = self.rs.uniform(-hs[1], hs[1], size=n)
        rz = self.rs.uniform(-hs[2], hs[2], size=n)

        # warning order np is z,y,x while itk is x,y,z
        x = self.source_img_info.spacing[2] * k + rz
        y = self.source_img_info.spacing[1] * j + ry
        z = self.source_img_info.spacing[0] * i + rx

        # x,y,z are in the image coord system
        # they are offset according to the coord system (image center or image offset)
        p = np.column_stack((x, y, z)) + self.points_offset + self.translation

        # rotation
        p = np.dot(p, self.rotation.T)

        # need direction ?
        if self.compute_directions is False:
            return p
        v = generate_isotropic_directions(n, rs=self.rs)
        v = np.dot(v, self.rotation.T)
        return np.column_stack((p, v))


class GANSource(GenericSource):
    """
    GAN source: the Generator produces particles
    Input is a neural network Generator trained with a GAN
    """

    type_name = "GANSource"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional param
        user_info.pth_filename = None
        user_info.position_keys = None
        user_info.backward_distance = None
        # if backward is enabled and the time is not managed by the GAN,
        # the time cannot be changed (yet). Use 'force' to enable backward
        user_info.backward_force = False
        user_info.direction_keys = None
        user_info.energy_key = None
        user_info.energy_min_threshold = -1
        user_info.energy_max_threshold = sys.float_info.max
        user_info.weight_key = None
        user_info.time_key = None
        user_info.relative_timing = True
        user_info.batch_size = 10000
        user_info.generator = None
        user_info.verbose_generator = False
        user_info.use_time = False
        user_info.use_weight = False
        # specific to conditional GAN
        user_info.cond_image = None
        user_info.compute_directions = False
        user_info.cond_debug = False
        # for skipped particles
        user_info.skip_policy = "SkipEvents"  # or ZeroEnergy
        # gpu or cpu or auto
        user_info.gpu_mode = "auto"

    def create_g4_source(self):
        return opengate_core.GateGANSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def initialize(self, run_timing_intervals):
        # FIXME -> check input user_info

        # initialize the mother class generic source
        GenericSource.initialize(self, run_timing_intervals)

        # default generator or set by the user
        if self.user_info.generator is None:
            self.set_default_generator()
        gen = self.user_info.generator

        # initialize the generator (read the GAN)
        # this function must have 1) the generator function 2) the associated info
        gen.initialize()

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(gen.generator)

        # set the parameters to the cpp side
        self.g4_source.SetGeneratorInfo(gen.gan_info)

    def set_default_generator(self):
        # non-conditional generator
        if self.user_info.cond_image is None:
            self.user_info.generator = GANSourceDefaultGenerator(self.user_info)
            return

        vcg = VoxelizedSourceConditionGenerator(self.user_info.cond_image, self)
        vcg.compute_directions = self.user_info.compute_directions
        g = GANSourceConditionalGenerator(self.user_info, vcg.generate_condition)
        self.user_info.generator = g


class GANPairsSource(GANSource):
    """
    GAN source: the Generator produces pairs of particles (for PET)
    Input is a neural network Generator trained with a GAN
    """

    type_name = "GANPairsSource"

    @staticmethod
    def set_default_user_info(user_info):
        GANSource.set_default_user_info(user_info)

    def create_g4_source(self):
        return opengate_core.GateGANPairSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def set_default_generator(self):
        # non-conditional generator
        if self.user_info.cond_image is None:
            self.user_info.generator = GANSourceDefaultPairsGenerator(self.user_info)
            return

        # conditional generator
        fatal(
            f"A conditional generator must be set in the "
            f"user_info.generator option of the GANPairsSource '{self.user_info.name}'."
        )


class GANSourceDefaultGenerator:
    """
    This class manage the base components of a particle generator.

    - In the constructor, the module 'gaga' is imported. It is only imported in the constructor to only required
    this module if it is used

    - 'initialize' function: the GAN is loaded and the list of keys is initialized

    - 'generator' function: default generator

    - 'get_output_keys' function: map the user defined keys to the ones of the generator. There are two usages, either
    with on single primary (3 values for position, direction), or paired primary (6 values).

    - 'move_backward' function: consider all particles positions and move their backward according to their direction,
    using the factor provided by the user in 'user_info.backward_distance'. This is useful to allow generating
    particles that do not intersect with the detector.

    - 'copy_generated_particle_to_g4' function: copy all the particles (pos, dir, time, energy) to the cpp part.

    """

    def __init__(self, user_info):
        self.user_info = user_info
        # self.gaga = None
        self.indexes_are_build = None
        self.lock = None
        self.initialize_is_done = False
        self.keys_output = None
        self.gan_info = None
        self.gpu_mode = None

    def __getstate__(self):
        self.lock = None
        # self.gaga = None
        self.gan_info = None
        return self.__dict__

    def initialize(self):
        self.lock = threading.Lock()
        with self.lock:
            self.gpu_mode = self.user_info.gpu_mode
            if not self.initialize_is_done:
                self.read_gan_and_keys()
                self.initialize_is_done = True

    def read_gan_and_keys(self):
        # allow converting str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        # FIXME check the number of params

        # read pth and create the gan info structure
        self.gan_info = Box()
        g = self.gan_info
        g.params, g.G, g.D, g.optim = gaga.load(
            self.user_info.pth_filename, self.gpu_mode
        )

        """
        gan_info structure
        - params    net params from gaga_phsp (including the keys)
        - G         Generator net
        - D         Discriminator net
        - optim     Info about net optimisation

        We analyse the keys and fill the following elements to initialize the GANSource
        - info.position_is_set_by_GAN
        - info.direction_is_set_by_GAN
        - info.energy_is_set_by_GAN
        - info.time_is_set_by_GAN
        - info.weight_is_set_by_GAN
        - info.timing_is_relative
        """

        # by default, the output keys are the same as the input keys
        # (could be changed later by some parameterization)
        if self.keys_output is None:
            g.params.keys_output = g.params.keys_list
        else:
            g.params.keys_output = self.keys_output

        # position,
        g.position_is_set_by_GAN = self.user_info.position_keys is not None
        g.direction_is_set_by_GAN = self.user_info.direction_keys is not None
        g.energy_is_set_by_GAN = self.user_info.energy_key is not None
        g.time_is_set_by_GAN = self.user_info.time_key is not None
        g.weight_is_set_by_GAN = self.user_info.weight_key is not None
        g.timing_is_relative = self.user_info.relative_timing

        # init the key index
        g.position_gan_index = -1
        g.direction_gan_index = -1
        g.energy_gan_index = -1
        g.time_gan_index = -1
        g.weight_gan_index = -1

    def get_output_keys(self):
        with self.lock:
            # (this is only performed once)
            if not self.indexes_are_build:
                self.get_output_keys_with_lock()
                self.indexes_are_build = True

    def get_output_keys_with_lock(self):
        n = self.user_info.batch_size
        g = self.gan_info
        the_keys = g.params.keys_output

        self.check_parameters(g)
        self.get_position_index(g, the_keys, n)
        self.get_direction_index(g, the_keys, n)
        self.get_energy_index(g, the_keys, n)
        self.get_time_index(g, the_keys, n)
        self.get_weight_index(g, the_keys, n)

    def check_parameters(self, g):
        # position
        if g.position_is_set_by_GAN and len(self.user_info.position_keys) != 3:
            dim = len(self.user_info.position_keys)
            self.fatal(f"you must provide 3 values for position, while it was {dim}")
        # direction
        if g.direction_is_set_by_GAN and len(self.user_info.direction_keys) != 3:
            dim = len(self.user_info.direction_keys)
            self.fatal(f"you must provide 3 values for direction, while it was {dim}")

    def fatal(self, txt):
        fatal(f"Error in the GANSource {self.user_info.name}: {txt}")

    def get_position_index(self, g, the_keys, n):
        # get position index from GAN (or a fixed value)
        if not g.position_is_set_by_GAN:
            return
        g.position_gan_index, g.position_use_index = self.get_gan_key_index(
            the_keys, self.user_info.position_keys, n
        )

    def get_direction_index(self, g, the_keys, n):
        # get position from GAN (or a fixed value)
        if not g.direction_is_set_by_GAN:
            return
        g.direction_gan_index, g.direction_use_index = self.get_gan_key_index(
            the_keys, self.user_info.direction_keys, n
        )

    def get_energy_index(self, g, the_keys, n):
        # get energy index from GAN
        if not g.energy_is_set_by_GAN:
            return
        g.energy_gan_index = the_keys.index(self.user_info.energy_key)

    def get_time_index(self, g, the_keys, n):
        # get time index from GAN
        if not g.time_is_set_by_GAN:
            return
        g.time_gan_index = the_keys.index(self.user_info.time_key)

    def get_weight_index(self, g, the_keys, n):
        # get weight index from GAN
        if not g.weight_is_set_by_GAN:
            return
        g.weight_gan_index = the_keys.index(self.user_info.weight_key)

    def get_gan_key_index(self, all_keys, user_keys, n):
        """
        Consider 'user_keys' in the list of all keys and return the indexes
        Special case: if the key name is a float value, we consider the value instead of the index.
        """
        p = []
        o = []  # true or false if used or not
        dim = len(user_keys)
        for i in range(dim):
            try:
                index = all_keys.index(user_keys[i])
                p.append(index)
                o.append(True)
            except:
                if type(user_keys[i]) == float:
                    p.append(np.ones(n) * user_keys[i])
                    o.append(False)
                else:
                    fatal(
                        f"Error, cannot use the key {user_keys[i]} (in {user_keys}) in the GAN source. "
                        f"GAN keys are: {all_keys}"
                    )
        return p, o

    def generator(self, source):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """
        # get the info
        g = self.gan_info
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            print(f"Generate {n} particles from GAN ", end="")

        # generate samples (this is the most time-consuming part)
        fake = gaga.generate_samples_non_cond(
            g.params,
            g.G,
            n=n,
            batch_size=n,
            normalize=False,
            to_numpy=True,
            silence=True,
        )

        # consider the names of the output keys position/direction/energy/time/weight
        self.get_output_keys()

        # move particle backward ?
        self.move_backward(g, fake)

        # copy to cpp
        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f"in {end - start:0.1f} sec (GPU={g.params.current_gpu_mode})")

    def copy_generated_particle_to_g4(self, source, g, fake):
        # get the index of from the GAN vector
        # (or some fixed values)

        # position
        if g.position_is_set_by_GAN:
            pos = []
            dim = len(g.position_gan_index)
            for i in range(dim):
                if g.position_use_index[i]:
                    pos.append(fake[:, g.position_gan_index[i]])
                else:
                    pos.append(g.position_gan_index[i])
            # copy to c++
            source.fPositionX = pos[0]
            source.fPositionY = pos[1]
            source.fPositionZ = pos[2]

        # direction
        if g.direction_is_set_by_GAN:
            dir = []
            dim = len(g.direction_gan_index)
            for i in range(dim):
                if g.direction_use_index[i]:
                    dir.append(fake[:, g.direction_gan_index[i]])
                else:
                    dir.append(g.direction_gan_index[i])
            # copy to c++
            source.fDirectionX = dir[0]
            source.fDirectionY = dir[1]
            source.fDirectionZ = dir[2]

        # energy
        if g.energy_is_set_by_GAN:
            # copy to c++
            source.fEnergy = fake[:, g.energy_gan_index]

        # time
        if g.time_is_set_by_GAN:
            # copy to c++
            source.fTime = fake[:, g.time_gan_index]

        # weight
        if g.weight_is_set_by_GAN:
            # copy to c++
            source.fWeight = fake[:, g.weight_gan_index]

    def move_backward(self, g, fake):
        # move particle backward ?
        back = self.user_info.backward_distance
        if not back:
            return

        if not g.time_is_set_by_GAN and not self.user_info.backward_force:
            fatal(
                f"If backward is enabled the time is not managed by GAN,"
                f" time is wrong. IT can be forced, however, with the option 'backward_force'"
            )

        # move particle position
        position = fake[:, g.position_gan_index[0] : g.position_gan_index[0] + 3]
        direction = fake[:, g.direction_gan_index[0] : g.direction_gan_index[0] + 3]
        fake[:, g.position_gan_index[0] : g.position_gan_index[0] + 3] = (
            position - back * direction
        )

        # modify the time because we move the particle backward
        if g.time_is_set_by_GAN:
            c = scipy.constants.speed_of_light * 1000 / 1e9  # in mm/ns
            xt = back / c
            fake[:, g.time_gan_index] -= xt


class GANSourceDefaultPairsGenerator(GANSourceDefaultGenerator):
    """
    Like GANSourceDefaultGenerator but for pairs of particle (PET)
    """

    def __init__(self, user_info):
        super().__init__(user_info)
        self.is_paired = True

    def __getstate__(self):
        self.lock = None
        self.gan_info = None
        return self.__dict__

    def check_parameters(self, g):
        # position
        if g.position_is_set_by_GAN and len(self.user_info.position_keys) != 6:
            dim = len(self.user_info.position_keys)
            self.fatal(f"you must provide 6 values for position, while it was {dim}")
        # direction
        if g.direction_is_set_by_GAN and len(self.user_info.direction_keys) != 6:
            dim = len(self.user_info.direction_keys)
            self.fatal(f"you must provide 6 values for direction, while it was {dim}")

    def get_energy_index(self, g, the_keys, n):
        # get energy index from GAN
        if not g.energy_is_set_by_GAN:
            return
        ek = self.user_info.energy_key
        dim = len(ek)
        if dim != 2:
            self.fatal(f"you must provide 2 values for energy, while it was {dim}")
        g.energy_gan_index = [the_keys.index(ek[0]), the_keys.index(ek[1])]

    def get_time_index(self, g, the_keys, n):
        # get time index from GAN
        if not g.time_is_set_by_GAN:
            return
        ek = self.user_info.time_key
        dim = len(ek)
        if dim != 2:
            self.fatal(f"you must provide 2 values for time, while it was {dim}")
        g.time_gan_index = [the_keys.index(ek[0]), the_keys.index(ek[1])]

    def get_weight_index(self, g, the_keys, n):
        # get weight index from GAN
        if not g.weight_is_set_by_GAN:
            return
        ek = self.user_info.weight_key
        dim = len(ek)
        if dim != 2:
            self.fatal(f"you must provide 2 values for weight, while it was {dim}")
        g.weight_gan_index = [the_keys.index(ek[0]), the_keys.index(ek[1])]

    def generator(self, source):
        """
        Main function that will be called from the cpp side every time a batch
        of particles should be created.
        Once created here, the particles are copied to cpp.
        (Yes maybe the copy could be avoided, but I did not manage to do it)
        """
        # get the info
        g = self.gan_info
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            print(f"Generate {n} particles from GAN ", end="")

        # generate samples (this is the most time-consuming part)
        fake = gaga.generate_samples_non_cond(
            g.params,
            g.G,
            n=n,
            batch_size=n,
            normalize=False,
            to_numpy=True,
            silence=True,
        )

        # consider the names of the output keys position/direction/energy/time/weight
        self.get_output_keys()

        # move particle backward ?
        self.move_backward(g, fake)

        # copy to cpp
        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f"in {end - start:0.1f} sec (device={g.params.current_gpu_device})")

    def copy_generated_particle_to_g4(self, source, g, fake):
        # position
        if g.position_is_set_by_GAN:
            pos = []
            dim = len(g.position_gan_index)
            for i in range(dim):
                if g.position_use_index[i]:
                    pos.append(fake[:, g.position_gan_index[i]])
                else:
                    pos.append(g.position_gan_index[i])
            # copy to c++
            source.fPositionX = pos[0]
            source.fPositionY = pos[1]
            source.fPositionZ = pos[2]
            source.fPositionX2 = pos[3]
            source.fPositionY2 = pos[4]
            source.fPositionZ2 = pos[5]

        # direction
        if g.direction_is_set_by_GAN:
            dir = []
            dim = len(g.direction_gan_index)
            for i in range(dim):
                if g.direction_use_index[i]:
                    dir.append(fake[:, g.direction_gan_index[i]])
                else:
                    dir.append(g.direction_gan_index[i])
            # copy to c++
            source.fDirectionX = dir[0]
            source.fDirectionY = dir[1]
            source.fDirectionZ = dir[2]
            source.fDirectionX2 = dir[3]
            source.fDirectionY2 = dir[4]
            source.fDirectionZ2 = dir[5]

        # energy
        if g.energy_is_set_by_GAN:
            # copy to c++
            source.fEnergy = fake[:, g.energy_gan_index[0]]
            source.fEnergy2 = fake[:, g.energy_gan_index[1]]

        # time
        if g.time_is_set_by_GAN:
            # copy to c++
            source.fTime = fake[:, g.time_gan_index[0]]
            source.fTime2 = fake[:, g.time_gan_index[1]]

        # weight
        if g.weight_is_set_by_GAN:
            # copy to c++
            source.fWeight = fake[:, g.weight_gan_index[0]]
            source.fWeight2 = fake[:, g.weight_gan_index[1]]

    def move_backward(self, g, fake):
        # move particle backward ?
        back = self.user_info.backward_distance
        if not back:
            return

        if not g.time_is_set_by_GAN and not self.user_info.backward_force:
            fatal(
                f"If backward is enabled the time is not managed by GAN,"
                f" time is wrong. IT can be forced, however, with the option 'backward_force'"
            )

        # move particle position
        position = fake[:, g.position_gan_index[0] : g.position_gan_index[0] + 3]
        direction = fake[:, g.direction_gan_index[0] : g.direction_gan_index[0] + 3]
        fake[:, g.position_gan_index[0] : g.position_gan_index[0] + 3] = (
            position - back * direction
        )

        # move second particle position
        position = fake[:, g.position_gan_index[3] : g.position_gan_index[3] + 3]
        direction = fake[:, g.direction_gan_index[3] : g.direction_gan_index[3] + 3]
        fake[:, g.position_gan_index[3] : g.position_gan_index[3] + 3] = (
            position - back * direction
        )

        # modify the time because we move the particle backward
        if g.time_is_set_by_GAN:
            c = scipy.constants.speed_of_light * 1000 / 1e9  # in mm/ns
            xt = back / c
            fake[:, g.time_gan_index[0]] -= xt
            fake[:, g.time_gan_index[1]] -= xt


class GANSourceConditionalGenerator(GANSourceDefaultGenerator):
    def __init__(self, user_info, generate_condition_function):
        super().__init__(user_info)
        self.generate_condition = generate_condition_function

    def generate_condition(self, n):
        fatal(
            f'Error: to use GANSourceConditionalGenerator,  you must provide a function "f" '
            f'that take a single int "n" as input and generate n condition samples. '
            f'This function "f" must be set with generator.generate_condition = f'
        )
        return None

    def generator(self, source):
        """
        Generate particles with a GAN, considering conditional vectors.
        """

        # get the info
        g = self.gan_info
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            print(f"Generate {n} particles from GAN ", end="")

        # generate cond
        cond = self.generate_condition(n)

        # generate samples (this is the most time-consuming part)
        if self.user_info.cond_debug:
            # debug : do not run GAN, only consider the conditions
            # needed by test 047
            fake = cond
        else:
            fake = gaga.generate_samples3(
                g.params,
                g.G,
                n=n,
                cond=cond,
            )

        # consider the names of the output keys position/direction/energy/time/weight
        self.get_output_keys()

        # if debug, the GAN is not used.
        if self.user_info.cond_debug:
            g.position_gan_index = [0, 1, 2]
            g.direction_gan_index = [3, 4, 5]
            g.energy_is_set_by_GAN = False
            g.energy_type = False

        # move particle backward ?
        self.move_backward(g, fake)

        # copy to cpp (g4)
        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f"in {end - start:0.2f} sec (GPU={g.params.current_gpu_mode})")


class GANSourceConditionalPairsGenerator(GANSourceDefaultPairsGenerator):
    """
    Generate pairs of particles with a GAN, considering conditional vectors.

    The parameter sphere_radius is required : it is the radius of the sphere
    that surround the source during the training.

    """

    def __init__(self, user_info, sphere_radius, generate_condition_function):
        super().__init__(user_info)
        self.sphere_radius = sphere_radius
        self.generate_condition = generate_condition_function

    def __getstate__(self):
        # needed to not pickle. Need to reset some attributes
        self.gan = None
        self.generate_condition = None
        self.lock = None
        return self.__dict__

    def generate_condition(self, n):
        fatal(
            f'Error: to use GANSourceConditionalPairsGenerator,  you must provide a function "f" '
            f'that take a single int "n" as input and generate n condition samples. '
            f'This function "f" must be set with generator.generate_condition = f'
        )
        return None

    def generator(self, source):
        # get the info
        g = self.gan_info
        n = self.user_info.batch_size
        start_time = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start_time = time.time()
            print(f"Generate {n} particles from GAN ", end="")

        # generate cond
        cond = self.generate_condition(n)

        # generate samples (this is the most time-consuming part)
        fake = gaga.generate_samples3(g.params, g.G, to_numpy=False, n=n, cond=cond)

        # parametrisation
        keys = g.params["keys_list"]
        if self.sphere_radius is None:
            fatal(
                f'Error the option "sphere_radius" must be set for the source "{self.user_info.name}"'
            )
        params = {
            "keys_list": keys,
            "radius": self.sphere_radius,
            "ignore_directions": False,
        }
        fake = gaga.from_tlor_to_pairs(fake, params)
        keys = params["keys_output"]
        g.params["keys_output"] = keys

        # consider the names of the output keys position/direction/energy/time/weight
        self.get_output_keys()

        # move particle backward ?
        self.move_backward(g, fake)

        # back from torch to numpy
        fake = fake.cpu().data.numpy()

        # copy to cpp
        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(
                f"in {end - start_time:0.1f} sec (device={g.params.current_gpu_device})"
            )
