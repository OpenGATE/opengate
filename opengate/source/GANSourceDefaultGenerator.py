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
        self.gaga = gate.import_gaga_phsp()
        self.indexes_are_build = None
        if self.gaga is None:
            print("Cannot run GANSource")
            sys.exit()
        self.lock = threading.Lock()
        self.initialize_is_done = False
        self.keys_output = None

    def __getstate__(self):
        self.lock = None
        self.gaga = None
        self.gan = None
        return self.__dict__

    def initialize(self):
        with self.lock:
            if not self.initialize_is_done:
                self.initialize_with_lock()
                self.initialize_is_done = True

    def initialize_with_lock(self):
        # allow converting str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        # read pth
        self.gan = Box()
        g = self.gan
        g.params, g.G, g.D, g.optim, g.dtypef = self.gaga.load(
            self.user_info.pth_filename, "auto", verbose=False
        )

        # by default, the output keys are the same as the input keys
        # (could be changed later by some parameterization)
        if self.keys_output is None:
            g.params.keys_output = g.params.keys_list
        else:
            g.params.keys_output = self.keys_output

        # check the number of params
        dim = len(self.user_info.position_keys)
        if dim != 3 and dim != 6:
            gate.fatal(
                f"In the source {self.user_info.name}, "
                f"position_keys size must be 3 or 6, while it is {dim}"
            )
        dim2 = len(self.user_info.direction_keys)
        if dim2 != dim:
            gate.fatal(
                f"In the source {self.user_info.name}, "
                f"direction_keys must have the same size as position_keys, while it is {dim2} and {dim}"
            )
        # if 3 only (not paired generation), the E, w and t are put in a vector
        if dim == 3:
            self.user_info.is_paired = False
            self.user_info.energy_key = [self.user_info.energy_key]
            if self.user_info.weight_key is not None:
                self.user_info.weight_key = [self.user_info.weight_key]
            if self.user_info.time_key is not None:
                self.user_info.time_key = [self.user_info.time_key]
        else:
            self.user_info.is_paired = True

    def get_output_keys(self):
        with self.lock:
            # (this is only performed once)
            if not self.indexes_are_build:
                self.get_output_keys_with_lock()
                self.indexes_are_build = True

    def get_output_keys_with_lock(self):
        g = self.gan

        # get position index from GAN (or a fixed value)
        k = g.params.keys_output
        n = self.user_info.batch_size
        dim = len(self.user_info.position_keys)
        g.position, g.position_type = self.get_key_generated_values(
            k, self.user_info.position_keys, n, dim=dim
        )

        # get position from GAN (or a fixed value)
        g.direction, g.direction_type = self.get_key_generated_values(
            k, self.user_info.direction_keys, n, dim=dim
        )

        # one primary or two primaries (paired) ?
        d = 1
        if self.user_info.is_paired:
            d = 2

        # get energy from GAN (or a fixed value)
        g.energy, g.energy_type = self.get_key_generated_values(
            k, self.user_info.energy_key, n, dim=d
        )

        # get weight from GAN (or a fixed value)
        if self.user_info.weight_key is not None:
            g.weight, g.weight_type = self.get_key_generated_values(
                k, self.user_info.weight_key, n, dim=d
            )

        # get time from GAN (or a fixed value)
        if self.user_info.time_key is not None:
            g.time, g.time_type = self.get_key_generated_values(
                k, self.user_info.time_key, n, dim=d
            )

    def get_key_generated_values(self, k, pk, n, dim=3):
        p = []
        o = []  # true or false if used or not
        for i in range(dim):
            try:
                index = k.index(pk[i])
                p.append(index)
                o.append(True)
            except:
                if type(pk[i]) == float:
                    p.append(np.ones(n) * pk[i])
                    o.append(False)
                else:
                    gate.fatal(
                        f"Error, cannot use the key {pk[i]} (in {pk}) in the GAN source. "
                        f"GAN keys are: {k}"
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
        g = self.gan
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
        # get the values from GAN or fixed value
        # the index are precomputed in get_key_generated_values
        # (this is a bit convoluted, but it does the job)
        pos = []
        dir = []
        dim = len(g.position)
        is_paired = self.user_info.is_paired

        # position, direction
        for i in range(dim):
            if g.position_type[i]:
                pos.append(fake[:, g.position[i]])
            else:
                pos.append(g.position[i])
            if g.direction_type[i]:
                dir.append(fake[:, g.direction[i]])
            else:
                dir.append(g.direction[i])

        # energy
        if g.energy_type:
            energy = []
            energy.append(fake[:, g.energy[0]])
            if is_paired:
                energy.append(fake[:, g.energy[1]])
        else:
            energy = g.energy

        # weight ? (fake if not used)
        weight = [0]
        if self.user_info.weight_key is not None:
            weight = []
            weight.append(fake[:, g.weight[0]])
            if is_paired:
                weight.append(fake[:, g.weight[1]])

        # time (fake if not used)
        the_time = [0]
        if self.user_info.time_key is not None:
            the_time = []
            the_time.append(fake[:, g.time[0]])
            if is_paired:
                the_time.append(fake[:, g.time[1]])

        # copy to c++
        source.fPositionX = pos[0]
        source.fPositionY = pos[1]
        source.fPositionZ = pos[2]

        # copy to c++
        source.fDirectionX = dir[0]
        source.fDirectionY = dir[1]
        source.fDirectionZ = dir[2]

        # copy to c++
        source.fEnergy = energy[0]
        if self.user_info.weight_key is not None:
            source.fWeight = weight[0]
        if self.user_info.time_key is not None:
            source.fTime = the_time[0]

        # pairs ?
        if is_paired:
            source.fPositionX2 = pos[3]
            source.fPositionY2 = pos[4]
            source.fPositionZ2 = pos[5]

            # copy to c++
            source.fDirectionX2 = dir[3]
            source.fDirectionY2 = dir[4]
            source.fDirectionZ2 = dir[5]

            # copy to c++
            source.fEnergy2 = energy[1]
            if self.user_info.weight_key is not None:
                source.fWeight2 = weight[1]
            if self.user_info.time_key is not None:
                source.fTime2 = the_time[1]

    def move_backward(self, g, fake):
        # move particle backward ?
        back = self.user_info.backward_distance
        if not back:
            return
        # move particle position
        position = fake[:, g.position[0] : g.position[0] + 3]
        direction = fake[:, g.direction[0] : g.direction[0] + 3]
        fake[:, g.position[0] : g.position[0] + 3] = position - back * direction

        # modify the time because we move the particle backward
        c = scipy.constants.speed_of_light * 1000 / 1e9  # in mm/ns
        xt = back / c
        if self.user_info.time_key is not None:
            fake[:, g.time[0]] -= xt

        if self.user_info.is_paired:
            # move second particle position
            position = fake[:, g.position[3] : g.position[3] + 3]
            direction = fake[:, g.direction[3] : g.direction[3] + 3]
            fake[:, g.position[3] : g.position[3] + 3] = position - back * direction
            if self.user_info.time_key is not None:
                fake[:, g.time[1]] -= xt
