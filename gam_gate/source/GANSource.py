import gam_gate as gan
from .GenericSource import *
import gam_g4 as g4
import sys
import time


class GANSource(GenericSource):
    """
    GAN source: the Generator produces particles
    Input is a neural network Generator trained with a GAN
    """

    type_name = 'GAN'

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional param
        user_info.pth_filename = None
        user_info.position_keys = None
        user_info.direction_keys = None
        user_info.energy_key = None
        user_info.weight_key = 1.0
        user_info.batch_size = 10000
        user_info.generator = None
        user_info.verbose_generator = False

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GamGANSource()

    def __init__(self, user_info):
        super().__init__(user_info)
        self.gan = None
        self.gaga = gan.import_gaga_phsp()
        if self.gaga is None:
            print("Cannot run GANSource")
            sys.exit()

    def initialize(self, run_timing_intervals):
        # FIXME -> check input user_info

        # allow to convert stuff like 1e5 to int
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

        # get energy from GAN or fixed value
        g.weight, g.weight_type = self.get_key_generated_values(k, [self.user_info.weight_key], n, dim=1)

        # initialize standard options (particle energy, etc)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)

        # set the generator, it could this default generator or another one
        # provided by user
        if self.user_info.generator is None:
            self.user_info.generator = self.default_generator
        self.g4_source.SetGeneratorFunction(self.user_info.generator)

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

    def default_generator(self, source):
        # generate samples
        g = self.gan
        n = self.user_info.batch_size
        if self.user_info.verbose_generator:
            start = time.time()
            print(f'Generate {n} particles from GAN '
                  f'{self.user_info.position_keys} {self.user_info.direction_keys}'
                  f' {self.user_info.energy_key} {self.user_info.weight_key} ...', end='')
            sys.stdout.flush()
        fake = self.gaga.generate_samples2(g.params, g.G, g.D,
                                      n=n,
                                      batch_size=n,
                                      normalize=False,
                                      to_numpy=True,
                                      silence=True)

        # get the values from GAN or fixed value
        # the index are precomputed in get_key_generated_values
        # (this is a bit convoluted, but it does the job)
        pos = []
        dir = []
        mm = gam.g4_units('mm')
        for i in range(3):
            if g.position_type[i]:
                pos.append(fake[:, g.position[i]] * mm)
            else:
                pos.append(g.position[i])
            if g.direction_type[i]:
                dir.append(fake[:, g.direction[i]])
            else:
                dir.append(g.direction[i])
        MeV = gam.g4_units('MeV')
        if g.energy_type:
            energy = fake[:, g.energy] / MeV
        else:
            energy = g.energy
        if g.weight_type:
            weight = fake[:, g.weight]
        else:
            weight = g.weight

        # copy to c++
        if self.user_info.verbose_generator:
            end = time.time()
            print(f' ({end - start:0.1f} sec) copy to G4 ... ', end='')
            sys.stdout.flush()
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

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f' done {fake.shape} {end - start:0.1f} sec (GPU={g.params.current_gpu})')
