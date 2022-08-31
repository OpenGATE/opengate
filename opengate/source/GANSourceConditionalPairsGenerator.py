from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
import sys
import time
import opengate as gate


class GANSourceConditionalPairsGenerator(GANSourceDefaultGenerator):
    def __init__(self, user_info):
        user_info.is_paired = True
        super().__init__(user_info)
        self.generate_condition = None
        self.cylinder_radius = None

    def generator(self, source):
        """
        Generate with GAN,
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
            to_numpy=False,  # next step is in torch, not numpy
            cond=cond,
            silence=True,
        )

        # parametrisation
        keys = g.params["keys_list"]
        if self.cylinder_radius is None:
            gate.fatal(
                f'Error the option "cylinder_radius" must be set for the source "{self.user_info.name}"'
            )
        params = {
            "keys_list": keys,
            "radius": self.cylinder_radius,
            "ignore_directions": False,
        }
        fake = self.gaga.from_tlor_to_pairs(fake, params)
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
            print(f" done in {end - start:0.1f} sec (GPU={g.params.current_gpu})")
