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
        Generate particles with a GAN, considering conditional vectors.
        """

        # get the info
        g = self.gan
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            print(f"Generate {n} particles from GAN ...", end="")
            sys.stdout.flush()

        # generate cond
        cond = self.generate_condition(n)

        # generate samples (this is the most time-consuming part)
        fake = self.gaga.generate_samples2(
            g.params,
            g.G,
            g.D,
            n=n,
            batch_size=n,
            normalize=False,
            to_numpy=True,
            cond=cond,
            silence=True,
        )

        # consider the names of the output keys position/direction/energy/time/weight
        self.get_output_keys()

        # move particle backward ?
        self.move_backward(g, fake)

        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f" done in {end - start:0.1f} sec (GPU={g.params.current_gpu})")
