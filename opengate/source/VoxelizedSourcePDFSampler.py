#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import bisect
import numpy as np
import itk
import opengate as gate
import opengate_core as g4


class VoxelizedSourcePDFSampler:
    """
    This is an alternative to GateSPSVoxelsPosDistribution (c++)
    It is needed because the cond voxel source is used on python side.

    There are two versions, version 2 is much slower (do not use)
    """

    def __init__(self, itk_image, version=1):
        self.image = itk_image
        self.version = version
        # get image in np array
        self.imga = itk.array_view_from_image(itk_image)
        imga = self.imga

        # image sizes
        lx = self.imga.shape[0]
        ly = self.imga.shape[1]
        lz = self.imga.shape[2]
        m = lx * ly * lz

        # normalized pdf
        pdf = imga.ravel(order="F")
        self.pdf = pdf / pdf.sum()

        # create grid of indices
        [x_grid, y_grid, z_grid] = np.meshgrid(
            np.arange(lx), np.arange(ly), np.arange(lz), indexing="ij"
        )

        # list of indices
        self.xi, self.yi, self.zi = (
            x_grid.ravel(order="F"),
            y_grid.ravel(order="F"),
            z_grid.ravel(order="F"),
        )

        # 1D indices
        self.linear_indices = np.arange(int(m))

        if version == 2:
            self.init_cdf()

        if version == 3:
            self.init_cdf()

        # ------------------------------------------
        # Below = NOT WORKING, DO NOT USE
        # create grid of indices in physical space
        """img_info = gate.get_info_from_image(self.image)
        sp = img_info.spacing
        hsp = sp / 2
        s = img_info.size * sp
        [px_grid, py_grid, pz_grid] = np.meshgrid(
            np.linspace(hsp[0], s[0] - hsp[0], lx),
            np.linspace(hsp[1], s[1] - hsp[1], lx),
            np.linspace(hsp[2], s[2] - hsp[2], lz),
            indexing='ij',
        )
        # list of indices
        self.pxi, self.pyi, self.pzi = (
            px_grid.ravel(order='F'),
            py_grid.ravel(order='F'),
            pz_grid.ravel(order='F'),
        )
        """
        # ------------------------------------------

    def init_cdf(self):
        self.cdf_x, self.cdf_y, self.cdf_z = gate.compute_image_3D_CDF(self.image)
        self.cdf_x = np.array(self.cdf_x)
        self.cdf_y = np.array(self.cdf_y)
        self.cdf_z = np.array(self.cdf_z)
        self.cdf_init = True

    def searchsorted2d(self, a, b):
        # https://stackoverflow.com/questions/56471109/how-to-vectorize-with-numpy-searchsorted-in-a-2d-array
        # Inputs : a is (m,n) 2D array and b is (m,) 1D array.
        # Finds np.searchsorted(a[i], b[i])) in a vectorized way by
        # scaling/offsetting both inputs and then using searchsorted

        # Get scaling offset and then scale inputs
        s = np.r_[0, (np.maximum(a.max(1) - a.min(1) + 1, b) + 1).cumsum()[:-1]]
        a_scaled = (a + s[:, None]).ravel()
        b_scaled = b + s

        # Use searchsorted on scaled ones and then subtract offsets
        return np.searchsorted(a_scaled, b_scaled) - np.arange(len(s)) * a.shape[1]

    def sample_indices_slower(self, n, rs=np.random):
        """
        This version seems slower than the other version with np random choice
        """
        # Z (here, search sorted is faster than bisect+loop)
        uz = rs.uniform(0, 1, size=n)
        # i = [bisect.bisect_left(self.cdf_z, uz[t], lo=0, hi=lz) for t in range(n)]
        i = np.searchsorted(self.cdf_z, uz, side="left")

        # Y, knowing Z
        # https://stackoverflow.com/questions/56471109/how-to-vectorize-with-numpy-searchsorted-in-a-2d-array
        ly = self.imga.shape[1]
        uy = rs.uniform(0, 1, size=n)
        j = [bisect.bisect_left(self.cdf_y[i[t]], uy[t], lo=0, hi=ly) for t in range(n)]

        # (here search sorted is not faster, we keep bisect)
        # slower:
        # cdfyi = np.take(self.cdf_y, i, axis=0)
        # j = self.searchsorted2d(cdfyi, uy)

        # X
        lx = self.imga.shape[2]
        ux = rs.uniform(0, 1, size=n)
        k = [
            bisect.bisect_left(self.cdf_x[i[t]][j[t]], ux[t], lo=0, hi=lx)
            for t in range(n)
        ]

        return i, j, k

    def samples_g4(self, n):
        # to compare with cpp version
        sps = g4.GateSPSVoxelsPosDistribution()
        sps.SetCumulativeDistributionFunction(self.cdf_z, self.cdf_y, self.cdf_x)
        p = np.array([sps.VGenerateOneDebug() for a in range(n)])
        return p[:, 2], p[:, 1], p[:, 0]

    def sample_indices(self, n, rs=np.random):
        indices = rs.choice(self.linear_indices, size=n, replace=True, p=self.pdf)
        i = self.xi[indices]
        j = self.yi[indices]
        k = self.zi[indices]
        return i, j, k

    def sample_indices_phys(self, n, rs=np.random):
        # TODO (not used yet)
        indices = rs.choice(self.linear_indices, size=n, replace=True, p=self.pdf)
        i = self.pxi[indices]
        j = self.pyi[indices]
        k = self.pzi[indices]
        return i, j, k
