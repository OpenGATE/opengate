from .GenericSource import *
import sys
import time
import scipy
import threading


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
        self.gaga = None
        self.indexes_are_build = None
        self.lock = None
        self.initialize_is_done = False
        self.keys_output = None
        self.gan_info = None

    def __getstate__(self):
        self.lock = None
        self.gaga = None
        self.gan_info = None
        return self.__dict__

    def initialize(self):
        self.lock = threading.Lock()
        with self.lock:
            if self.gaga is None:
                self.gaga = gate.import_gaga_phsp()
            if self.gaga is None:
                print("Cannot run GANSource, gaga_phsp not installed?")
                sys.exit()
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
        g.params, g.G, g.D, g.optim, g.dtypef = self.gaga.load(
            self.user_info.pth_filename, "auto", verbose=False
        )

        """
        gan_info structure
        - params    net params from gaga_phsp (including the keys)
        - G         Generator net
        - D         Discriminator net
        - optim     Info about net optimisation
        - dtypef    CPU or GPU

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
        gate.fatal(f"Error in the GANSource {self.user_info.name}: {txt}")

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
                    gate.fatal(
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
        fake = self.gaga.generate_samples2(
            g.params,
            g.G,
            g.D,
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
            print(f"in {end - start:0.1f} sec (GPU={g.params.current_gpu})")

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
            gate.fatal(
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
