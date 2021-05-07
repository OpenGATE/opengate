from .GenericSource import *
import gam_g4 as g4
import itk
import numpy as np
import matplotlib.pyplot as plt


class VoxelsSource(GenericSource):
    """
    Voxels source for 3D distributed activity
    """

    type_name = 'Voxels'

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)
        # remove position options
        # FIXME LATER delattr(user_info, 'position')
        # image
        user_info.image = None
        user_info.img_coord_system = False

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GamVoxelsSource()

    def __init__(self, user_info):  # FIXME needed ?
        super().__init__(user_info)

    def set_translation_from_image(self):
        print('ici')
        # compute the translation needed to
        # set the source in the same coordinate system
        # than the CT to which it is attached
        vol_name = self.user_info.mother
        f = self.simulation.get_volume_info(vol_name).image
        print(f)
        # FIXME use ReadImageInfo (read header only)

        img = itk.imread(f)
        info = gam.get_img_info(img)
        print('ct', info)

        # find center of the img
        img_center = info.size / 2.0
        # convert in img coord system
        img_center = itk.ContinuousIndex[itk.D, 3](img_center)
        p = img.TransformContinuousIndexToPhysicalPoint(img_center)
        print('center', img_center, p)

        # find center of the src
        src_info = gam.get_img_info(self.image)
        print('src', src_info)
        src_center = src_info.size / 2.0
        # convert in img coord system (assume it is the same than ct)
        src_center = itk.ContinuousIndex[itk.D, 3](src_center)
        q = self.image.TransformContinuousIndexToPhysicalPoint(src_center)
        print('center', src_center, q)

        # compute translation bw both centers
        tr = q-p
        self.user_info.translation = tr
        print(tr)
        tr = gam.vec_np_as_g4(np.array(tr))
        print(tr)

        # set translation to the position generator
        pg = self.g4_source.GetSPSVoxelPosDistribution()
        pg.SetImageSpacing(self.image.GetSpacing())
        pg.SetTranslation(tr)

        # reader = itk.ImageFileReader.New(FileName=f)
        # print(reader)
        # img = reader.ReadImageInformation()
        # print(img)

        #exit(0)

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
        # Check user_info type
        print('fixme initialize check user info source')

        # initialize standard options (particle energy, etc)
        GenericSource.initialize(self, run_timing_intervals)

        # read image
        self.image = itk.imread(self.user_info.image)

        # position
        vol_name = self.user_info.mother
        vol_type = self.simulation.get_volume_info(vol_name).type_name
        print(vol_name, vol_type)
        if vol_type == 'Image' and not self.user_info.img_coord_system:
            gam.warning(f'VoxelSource "{self.user_info.name}" has '
                        f'the flag img_coord_system set to True, '
                        f'but it is not attached to an Image '
                        f'volume ("{vol_name}", of type "{vol_type}"). '
                        f'So the flag is ignored.')
        if vol_type == 'Image' and self.user_info.img_coord_system:
            self.set_translation_from_image()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()
