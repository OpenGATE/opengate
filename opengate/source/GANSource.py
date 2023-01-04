from .GenericSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator


class GANSource(GenericSource):
    """
    GAN source: the Generator produces particles
    Input is a neural network Generator trained with a GAN
    """

    type_name = "GAN"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional param
        user_info.pth_filename = None
        user_info.position_keys = None
        user_info.backward_distance = None
        user_info.direction_keys = None
        user_info.energy_key = None
        user_info.energy_threshold = -1
        user_info.weight_key = None
        user_info.time_key = None
        user_info.time_relative = True
        user_info.batch_size = 10000
        user_info.generator = None
        user_info.verbose_generator = False
        user_info.is_paired = False
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

    """def __getstate__(self):
        super().__getstate__()
        for v in self.__dict__:
            print("state", v, self.__dict__[v])
        gen = self.user_info.generator
        for v in gen.__dict__:
            print("gen state", v)
        return self.__dict__"""

    def initialize(self, run_timing_intervals):
        # FIXME -> check input user_info

        # initialize the mother class generic source
        GenericSource.initialize(self, run_timing_intervals)

        # default generator or set by the user
        if self.user_info.generator is None:
            if self.user_info.cond_image is not None:
                voxelized_cond_generator = gate.VoxelizedSourceConditionGenerator(
                    self.user_info.cond_image, self
                )
                voxelized_cond_generator.compute_directions = (
                    self.user_info.compute_directions
                )
                gen = gate.GANSourceConditionalGenerator(
                    self.user_info,
                    voxelized_cond_generator.generate_condition,
                )
                self.user_info.generator = gen
            else:
                self.user_info.generator = GANSourceDefaultGenerator(self.user_info)

        # initialize the generator
        self.user_info.generator.initialize()

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(self.user_info.generator.generator)

        # weight ?
        if self.user_info.weight_key is None:
            self.g4_source.fUseWeight = False
        else:
            self.g4_source.fUseWeight = True

        # time ?
        if self.user_info.time_key is None:
            self.g4_source.fUseTime = False
        else:
            self.g4_source.fUseTime = True
            self.g4_source.fUseTimeRelative = self.user_info.time_relative
