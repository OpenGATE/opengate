import itk
from box import Box
from scipy.spatial.transform import Rotation

import opengate_core
from .generic import GenericSource
from ..image import (
    read_image_info,
    update_image_py_to_cpp,
    compute_image_3D_CDF,
)
from ..utility import ensure_filename_is_str


class VoxelsSource(GenericSource):
    """
    Voxels source for 3D distributed activity.
    Sampled with cumulative distribution functions.
    """

    type_name = "VoxelsSource"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional option: image and coord_syst
        user_info.image = None
        # add position translation
        user_info.position = Box()
        user_info.position.translation = [0, 0, 0]
        user_info.position.confine = None
        # no rotation for the moment
        user_info.position.rotation = Rotation.identity().as_matrix()
        # default values
        user_info.direction.type = "iso"
        user_info.energy.type = "mono"
        user_info.energy.mono = 0

    def __init__(self, user_info):
        ## FIXME
        super().__init__(user_info)
        self.image = None

    def __getstate__(self):
        super().__getstate__()
        self.image = None
        return self.__dict__

    def create_g4_source(self):
        return opengate_core.GateVoxelsSource()

    def set_transform_from_user_info(self):
        # get source image information
        src_info = read_image_info(str(self.user_info.image))
        # get pointer to SPSVoxelPosDistribution
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        # update cpp image info (no need to allocate)
        update_image_py_to_cpp(self.image, pg.cpp_edep_image, False)
        # set spacing
        pg.cpp_edep_image.set_spacing(src_info.spacing)
        # set origin (half size + translation and half pixel shift)
        c = (
            -src_info.size / 2.0 * src_info.spacing
            + self.user_info.position.translation
            + src_info.spacing / 2.0
        )
        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self):
        """
        Compute the Cumulative Distribution Function of the image
        Composed of: CDF_Z = 1D, CDF_Y = 2D, CDF_X = 3D
        """
        cdf_x, cdf_y, cdf_z = compute_image_3D_CDF(self.image)

        # set CDF to the position generator
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)

    def initialize(self, run_timing_intervals):
        # read source image
        self.image = itk.imread(ensure_filename_is_str(self.user_info.image))

        # compute position
        self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()

        # initialize standard options (particle energy, etc)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)
