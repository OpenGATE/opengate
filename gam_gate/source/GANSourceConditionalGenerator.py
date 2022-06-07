from .GenericSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
import sys
import time


class GANSourceConditionalGenerator(GANSourceDefaultGenerator):

    def __init__(self, user_info):
        super().__init__(user_info)
        self.generate_condition = None

    def generator(self, source):
        """
            TODO
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
                  f' {self.user_info.energy_key} {self.user_info.weight_key} ...', end='')
            sys.stdout.flush()

        # generate cond
        cond = self.generate_condition(n)

        # generate samples (this is the most time-consuming part)
        fake = self.gaga.generate_samples2(g.params, g.G, g.D,
                                           n=n,
                                           batch_size=n,
                                           normalize=False,
                                           to_numpy=True,
                                           cond=cond,
                                           silence=True)

        self.copy_generated_particle_to_g4(source, g, fake, start)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f' done {fake.shape} {end - start:0.1f} sec (GPU={g.params.current_gpu})')
