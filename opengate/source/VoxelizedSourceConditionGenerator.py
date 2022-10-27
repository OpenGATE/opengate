import opengate as gate
from .VoxelizedSourcePDFSampler import *


class VoxelizedSourceConditionGenerator:
    def __init__(self, activity_source_filename, rs=np.random):
        self.activity_source_filename = str(activity_source_filename)
        self.image = None
        self.cdf_x = self.cdf_y = self.cdf_z = None
        self.rs = rs
        self.img_info = None
        self.sampler = None
        self.initialize_source()
        self.compute_directions = False

    def initialize_source(self):
        self.image = itk.imread(self.activity_source_filename)
        self.img_info = gate.get_info_from_image(self.image)
        self.sampler = VoxelizedSourcePDFSampler(self.image)
        self.rs = np.random

    def generate_condition(self, n):
        # i j k is in np array order = z y x
        # but img_info is in the order x y z
        i, j, k = self.sampler.sample_indices(n, self.rs)

        # half pixel size
        hs = self.img_info.spacing / 2.0

        # sample within the voxel
        rx = self.rs.uniform(-hs[0], hs[0], size=n)
        ry = self.rs.uniform(-hs[1], hs[1], size=n)
        rz = self.rs.uniform(-hs[2], hs[2], size=n)

        # warning order np is z,y,x while itk is x,y,z
        x = self.img_info.spacing[2] * k + rz
        y = self.img_info.spacing[1] * j + ry
        z = self.img_info.spacing[0] * i + rx

        # x,y,z are in the image coord system
        # we set in the g4 coord system: according to the center of the image
        p = np.column_stack((x, y, z)) - hs * self.img_info.size + hs

        # need direction ?
        if self.compute_directions:
            v = gate.generate_isotropic_directions(n, rs=self.rs)
            return np.column_stack((p, v))
        else:
            return p
