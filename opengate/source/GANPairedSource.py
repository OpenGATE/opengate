from .GANSource import *
from .GANSourceDefaultGenerator import GANSourceDefaultGenerator


class GANPairSource(GANSource):
    """
    GAN source: the Generator produces pairs of particles (for PET)
    Input is a neural network Generator trained with a GAN
    """

    type_name = "GANPairSource"

    @staticmethod
    def set_default_user_info(user_info):
        GANSource.set_default_user_info(user_info)

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GateGANPairSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def initialize(self, run_timing_intervals):
        # FIXME -> check input user_info

        # initialize the mother class generic source
        GANSource.initialize(self, run_timing_intervals)

        """# default generator or set by the user
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
    """
