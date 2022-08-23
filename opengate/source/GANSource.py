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
            self.user_info.generator = GANSourceDefaultGenerator(self.user_info)

        # initialize the generator
        self.user_info.generator.initialize()

        # set the function pointer to the cpp side
        self.g4_source.SetGeneratorFunction(self.user_info.generator.generator)

        # weight ?
        print("initialize", self.user_info)
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
