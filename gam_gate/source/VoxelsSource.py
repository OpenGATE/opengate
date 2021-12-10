from .GenericSource import *
import gam_g4 as g4
import itk
import numpy as np


class VoxelsSource(GenericSource):
    """
    Voxels source for 3D distributed activity.
    Sampled with cumulative distribution functions.
    """

    type_name = 'Voxels'

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # additional option: image and coord_syst
        user_info.image = None
        user_info.img_coord_system = False
        # add position translation
        user_info.position = Box()
        user_info.position.translation = [0, 0, 0]
        user_info.position.confine = None
        # no rotation for the moment
        user_info.position.rotation = Rotation.identity().as_matrix()
        # default values
        user_info.direction.type = 'iso'
        user_info.energy.type = 'mono'
        user_info.energy.mono = 0

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GamVoxelsSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def set_transform_from_image(self):
        # we consider the coordinate system of the source image is the
        # same than the one from the image it is attached with, plus the translation
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        gam.update_image_py_to_cpp(self.image, pg.cpp_edep_image, False)
        src_info = gam.get_image_info(self.image)
        pg.cpp_edep_image.set_origin(src_info.origin + self.user_info.position.translation)

    def set_transform_from_user_info(self):
        # get source image information
        src_info = gam.get_image_info(self.image)
        # get pointer to SPSVoxelPosDistribution
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        # set spacing
        pg.cpp_edep_image.set_spacing(src_info.spacing)
        # set origin (half size + translation)
        c = -src_info.size / 2.0 * src_info.spacing
        c += self.user_info.position.translation
        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self):
        """
            Compute the Cumulative Distribution Function of the image
            Composed of: CDF_Z = 1D, CDF_Y = 2D, CDF_Z = 3D
        """
        # get image as 3D array, warning numpy is ZYX (while itk is XYZ)
        array = itk.array_view_from_image(self.image)
        # Sum image on a single plane along X axis
        sumx = np.sum(array, axis=2)
        # Y axis, sum plane on a single axis along Y axis
        sumxy = np.sum(sumx, axis=1)

        # X CDF
        cdf_x = []
        for i in range(array.shape[0]):  # Z
            cdf_x.append([])
            for j in range(array.shape[1]):  # Y
                # cumulated sum along X axis
                t = np.cumsum(array[i][j])
                # normalise if last value (sum) is not zero
                if t[-1] != 0:
                    t = t / t[-1]
                cdf_x[i].append(t)

        # Y CDF
        cdf_y = []
        for i in range(len(sumx)):  # Z
            t = np.cumsum(sumx[i])
            if t[-1] != 0:
                t = t / t[-1]
            cdf_y.append(t)

        # Z CDF
        cdf_z = np.cumsum(sumxy) / np.sum(sumxy)

        # set CDF to the position generator
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)

    def initialize(self, run_timing_intervals):
        # read source image
        self.image = itk.imread(gam.check_filename_type(self.user_info.image))

        # position relative to an image ?
        vol_name = self.user_info.mother
        vol_type = self.simulation.get_volume_user_info(vol_name).type_name
        if not vol_type == 'Image' and self.user_info.img_coord_system:
            gam.warning(f'VoxelSource "{self.user_info.name}" has '
                        f'the flag img_coord_system set to True, '
                        f'but it is not attached to an Image '
                        f'volume ("{vol_name}", of type "{vol_type}"). '
                        f'So the flag is ignored.')
        if vol_type == 'Image' and self.user_info.img_coord_system:
            self.set_transform_from_image()
        else:
            self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()

        # initialize standard options (particle energy, etc)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)
