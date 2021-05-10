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
        # no rotation for the moment
        # user_info.position.rotation = Rotation.identity().as_matrix()
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

    def set_translation_from_image(self):
        # compute the translation needed to
        # set the source in the same coordinate system
        # than the CT to which it is attached
        vol_name = self.user_info.mother
        f = self.simulation.get_volume_info(vol_name).image

        # FIXME use ReadImageInfo (read header only)
        img = itk.imread(f)
        info = gam.get_img_info(img)

        # find center of the img
        img_center = info.size / 2.0
        # convert in img coord system
        img_center = itk.ContinuousIndex[itk.D, 3](img_center)
        p = img.TransformContinuousIndexToPhysicalPoint(img_center)

        # find center of the src
        src_info = gam.get_img_info(self.image)
        src_center = src_info.size / 2.0
        # convert in img coord system (assume it is the same than ct)
        src_center = itk.ContinuousIndex[itk.D, 3](src_center)
        q = self.image.TransformContinuousIndexToPhysicalPoint(src_center)

        # compute translation bw both centers
        tr = q - p

        # set translation to the position generator
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        pg.SetImageSpacing(self.image.GetSpacing())
        pg.SetImageCenter(src_info.size / 2.0 * src_info.spacing)
        pg.SetTranslation(tr + self.user_info.position.translation)
        pg.InitializeOffset()

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
        pg.SetImageSpacing(self.image.GetSpacing())

    def initialize(self, run_timing_intervals):
        # initialize standard options (particle energy, etc)
        # we temporarily set the position attribute to reuse
        # the GenericSource verification
        GenericSource.initialize(self, run_timing_intervals)

        # read source image
        self.image = itk.imread(self.user_info.image)

        # position of the voxel source:
        # (- rotation is in user_info.position.rotation, read from c++) --> no rotation yet
        # - translation in user_info.position.center is set here with SetTranslation
        # - if img_coord_system, translation to center the volumes are added to the previous translation

        # position
        vol_name = self.user_info.mother
        vol_type = self.simulation.get_volume_info(vol_name).type_name
        if not vol_type == 'Image' and self.user_info.img_coord_system:
            gam.warning(f'VoxelSource "{self.user_info.name}" has '
                        f'the flag img_coord_system set to True, '
                        f'but it is not attached to an Image '
                        f'volume ("{vol_name}", of type "{vol_type}"). '
                        f'So the flag is ignored.')
        if vol_type == 'Image' and self.user_info.img_coord_system:
            self.set_translation_from_image()
        else:
            # set translation to the position generator
            pg = self.g4_source.GetSPSVoxelPosDistribution()
            pg.SetImageSpacing(self.image.GetSpacing())
            src_info = gam.get_img_info(self.image)
            pg.SetImageCenter(src_info.size / 2.0 * src_info.spacing)
            pg.SetTranslation(self.user_info.position.translation)
            pg.InitializeOffset()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()
