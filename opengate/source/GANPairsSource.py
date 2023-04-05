from .GANSource import *
from .GANSourceDefaultPairsGenerator import GANSourceDefaultPairsGenerator


class GANPairsSource(GANSource):
    """
    GAN source: the Generator produces pairs of particles (for PET)
    Input is a neural network Generator trained with a GAN
    """

    type_name = "GANPairsSource"

    @staticmethod
    def set_default_user_info(user_info):
        GANSource.set_default_user_info(user_info)

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GateGANPairSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def set_default_generator(self):
        # non-conditional generator
        if self.user_info.cond_image is None:
            self.user_info.generator = GANSourceDefaultPairsGenerator(self.user_info)
            return

        # conditional generator
        gate.fatal(
            f"A conditional generator must be set in the "
            f"user_info.generator option of the GANPairsSource '{self.user_info.name}'."
        )
