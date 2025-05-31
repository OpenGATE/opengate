import itk

import opengate_core as g4
from .generic import GenericSource
from ..image import (
    read_image_info,
    update_image_py_to_cpp,
    compute_image_3D_CDF,
)
from ..utility import ensure_filename_is_str
from ..base import process_cls


class VoxelSource(GenericSource, g4.GateVoxelSource):
    """
    VoxelSource = 3D activity distribution.
    Sampled with cumulative distribution functions.
    """

    # hints for IDE
    image: str

    user_info_defaults = {
        "image": (
            None,
            {
                "doc": "Filename of the image of the 3D activity distribution "
                "(will be automatically normalized to sum=1)",
                "is_input_file": True,
            },
        )
    }

    def __init__(self, *args, **kwargs):
        self.__initcpp__()
        super().__init__(self, *args, **kwargs)
        # the loaded image
        self.itk_image = None

    def __initcpp__(self):
        g4.GateVoxelSource.__init__(self)

    def set_transform_from_user_info(self):
        # get source image information
        src_info = read_image_info(str(self.image))
        # get the pointer to SPSVoxelPosDistribution
        pg = self.GetSPSVoxelPosDistribution()
        # update cpp image info (no need to allocate)
        update_image_py_to_cpp(self.itk_image, pg.cpp_edep_image, False)
        # set spacing
        pg.cpp_edep_image.set_spacing(src_info.spacing)
        # set origin (half size + translation and half-pixel shift)
        c = (
            -src_info.size / 2.0 * src_info.spacing
            + self.position.translation
            + src_info.spacing / 2.0
        )
        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self):
        """
        Compute the Cumulative Distribution Function of the image
        Composed of: CDF_Z = 1D, CDF_Y = 2D, CDF_X = 3D
        """
        cdf_x, cdf_y, cdf_z = compute_image_3D_CDF(self.itk_image)

        # set CDF to the position generator
        pg = self.GetSPSVoxelPosDistribution()
        pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)

    def initialize(self, run_timing_intervals):
        # read source image
        self.itk_image = itk.imread(ensure_filename_is_str(self.image))

        # compute position
        self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()

        # FIXME -> check other option in position not used here

        # initialise standard options (particle energy, etc.)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)


process_cls(VoxelSource)
