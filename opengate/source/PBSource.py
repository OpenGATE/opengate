import opengate as gate
from .GenericSource import *
import opengate_core as g4
import numpy as np


class PBSource(GenericSource):
    """
    PB source
    """

    type_name = "PB"

    @staticmethod
    def set_default_user_info(user_info):

        GenericSource.set_default_user_info(user_info)
        # additional parameters
        # position
        user_info.position = (
            Box()
        )  # Box() resets the object to blank. All param set for position before this line are cancelled
        user_info.position.type = "disc"
        user_info.position.size = [0, 0, 0]
        user_info.position.translation = [0, 0, 0]
        user_info.position.rotation = Rotation.identity().as_matrix()
        user_info.position.confine = None
        # direction
        user_info.direction.partPhSp_x = [
            0,
            0,
            0,
            0,
        ]  # sigma, theta, epsilon, conv (0: divergent, 1:convergent)
        user_info.direction.partPhSp_y = [0, 0, 0, 0]

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GatePBSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def set_transform_from_user_info(self):
        pass
        # get source image information

    #        src_info = gate.read_image_info(str(self.user_info.image))
    #        # get pointer to SPSVoxelPosDistribution
    #        pg = self.g4_source.GetSPSVoxelPosDistribution()
    #        # update cpp image info (no need to allocate)
    #        gate.update_image_py_to_cpp(self.image, pg.cpp_edep_image, False)
    #        # set spacing
    #        pg.cpp_edep_image.set_spacing(src_info.spacing)
    #        # set origin (half size + translation and half pixel shift)
    #        c = -src_info.size / 2.0 * src_info.spacing + self.user_info.position.translation + src_info.spacing / 2.0
    #        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self):
        """
        Compute the Cumulative Distribution Function of the image
        Composed of: CDF_Z = 1D, CDF_Y = 2D, CDF_X = 3D
        """
        pass

    #        cdf_x, cdf_y, cdf_z = gate.compute_image_3D_CDF(self.image)
    #
    #        # set CDF to the position generator
    #        pg = self.g4_source.GetSPSVoxelPosDistribution()
    #        pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)

    def initialize(self, run_timing_intervals):
        # read source image

        # compute position
        self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        # self.cumulative_distribution_functions()

        # initialize standard options (particle energy, etc)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)
