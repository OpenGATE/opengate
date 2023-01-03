import threading

from .GenericSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
import time


class GANSourceConditionalGenerator(GANSourceDefaultGenerator):
    def __init__(self, user_info, generate_condition_function):
        super().__init__(user_info)
        self.generate_condition = generate_condition_function

    def __getstate__(self):
        super().__getstate__()
        # we cannot pickle this function (not fully sure why)
        self.generate_condition = None
        return self.__dict__

    def generate_condition(self, n):
        gate.fatal(
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
        g = self.gan
        n = self.user_info.batch_size
        start = None

        # verbose and timing ?
        if self.user_info.verbose_generator:
            start = time.time()
            # tid = threading.currentThread().getName()
            print(f"Generate {n} particles from GAN ", end="")

        # generate cond
        cond = self.generate_condition(n)

        # generate samples (this is the most time-consuming part)
        if self.user_info.cond_debug:
            # debug : do not run GAN, only consider the conditions
            # needed by test 047
            fake = cond
        else:
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

        # if debug, the GAN is not used.
        if self.user_info.cond_debug:
            g.position = [0, 1, 2]
            g.direction = [3, 4, 5]
            g.energy_type = False

        # move particle backward ?
        self.move_backward(g, fake)

        # copy to cpp (g4)
        self.copy_generated_particle_to_g4(source, g, fake)

        # verbose
        if self.user_info.verbose_generator:
            end = time.time()
            print(f"in {end - start:0.2f} sec (GPU={g.params.current_gpu})")
