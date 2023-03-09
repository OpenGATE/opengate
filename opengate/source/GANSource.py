from .GenericSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator
import sys


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

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GateGANSource()

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

        vcg = gate.VoxelizedSourceConditionGenerator(self.user_info.cond_image, self)
        vcg.compute_directions = self.user_info.compute_directions
        g = gate.GANSourceConditionalGenerator(self.user_info, vcg.generate_condition)
        self.user_info.generator = g
