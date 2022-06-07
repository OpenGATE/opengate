from .GenericSource import *
import sys
import time


class GANSourceDefaultGenerator:

    def __init__(self, user_info):
        self.user_info = user_info
        self.gaga = gam.import_gaga_phsp()
        if self.gaga is None:
            print("Cannot run GANSource")
            sys.exit()

    def initialize(self):
        # allow to convert str like 1e5 to int
        self.user_info.batch_size = int(float(self.user_info.batch_size))

        # read pth
        self.gan = Box()
        g = self.gan
        g.params, g.G, g.D, g.optim, g.dtypef = self.gaga.load(self.user_info.pth_filename, 'auto', verbose=False)

        # get position index from GAN or fixed value
        k = g.params.keys_list
        n = self.user_info.batch_size
        g.position, g.position_type = self.get_key_generated_values(k, self.user_info.position_keys, n)

        # get position from GAN or fixed value
        g.direction, g.direction_type = self.get_key_generated_values(k, self.user_info.direction_keys, n)

        # get energy from GAN or fixed value
        g.energy, g.energy_type = self.get_key_generated_values(k, [self.user_info.energy_key], n, dim=1)

        # get weight from GAN or fixed value
        if self.user_info.weight_key is not None:
            g.weight, g.weight_type = self.get_key_generated_values(k, [self.user_info.weight_key], n, dim=1)

        # get time from GAN or fixed value
        if self.user_info.time_key is not None:
            g.time, g.time_type = self.get_key_generated_values(k, [self.user_info.time_key], n, dim=1)

    def get_key_generated_values(self, k, pk, n, dim=3):
        p = []
        o = []
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
                    gam.fatal(f'Error, cannot use the key {pk[i]} (in {pk}) in the GAN source. '
                              f'GAN keys are: {k}')
        if dim == 1:
            return p[0], o[0]
        return p, o

    def generator(self, source):
        """
            Main function that will be called from the cpp side every time a batch
            of particles should be created.
            Once created here, the particles are copied to cpp.
            (Yes maybe the copy could be avoided, but I did not manage)
        """
        # get the info
        g = self.gan
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            print(f'Generate {n} particles from GAN '
                  f'{self.user_info.position_keys} {self.user_info.direction_keys}'
                  f' E={self.user_info.energy_key}'
                  f' w={self.user_info.weight_key}'
                  f' t={self.user_info.time_key} ...', end='')
            sys.stdout.flush()

        # generate samples (this is the most time-consuming part)
        fake = self.gaga.generate_samples2(g.params, g.G, g.D,
                                           n=n,
                                           batch_size=n,
                                           normalize=False,
                                           to_numpy=True,
                                           silence=True)

        self.copy_generated_particle_to_g4(source, g, fake, start)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f' done {fake.shape} {end - start:0.1f} sec (GPU={g.params.current_gpu})')

    def copy_generated_particle_to_g4(self, source, g, fake, start=None):
        mm = gam.g4_units('mm')
        MeV = gam.g4_units('MeV')
        ns = gam.g4_units('ns')

        # get the values from GAN or fixed value
        # the index are precomputed in get_key_generated_values
        # (this is a bit convoluted, but it does the job)
        pos = []
        dir = []
        for i in range(3):
            if g.position_type[i]:
                pos.append(fake[:, g.position[i]] * mm)
            else:
                pos.append(g.position[i])
            if g.direction_type[i]:
                dir.append(fake[:, g.direction[i]])
            else:
                dir.append(g.direction[i])
        if g.energy_type:
            energy = fake[:, g.energy] / MeV
            print('energy generated ', MeV, np.mean(energy))
        else:
            energy = g.energy

        # weight ? (fake if not used)
        weight = [0]
        if self.user_info.weight_key is not None:
            weight = fake[:, g.weight]

        # time ? (fake if not used)
        the_time = [0]
        if self.user_info.time_key is not None:
            the_time = fake[:, g.time] * ns

        # verbose ?
        if self.user_info.verbose_generator:
            end = time.time()
            print(f' ({end - start:0.1f} sec) copy to G4 ... ', end='')
            sys.stdout.flush()

        # copy to c++
        source.fPositionX = pos[0]
        source.fPositionY = pos[1]
        source.fPositionZ = pos[2]

        # copy to c++
        source.fDirectionX = dir[0]
        source.fDirectionY = dir[1]
        source.fDirectionZ = dir[2]

        # copy to c++
        source.fEnergy = energy
        source.fWeight = weight
        source.fTime = the_time
