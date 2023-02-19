from .GenericSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
import time
import scipy


class GANSourceDefaultPairsGenerator(GANSourceDefaultGenerator):
    """
    Like GANSourceDefaultGenerator but for pairs of particle (PET)
    """

    def __init__(self, user_info):
        super().__init__(user_info)
        self.is_paired = True

    def __getstate__(self):
        self.lock = None
        self.gaga = None
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
