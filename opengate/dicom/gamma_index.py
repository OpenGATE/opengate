# -----------------------------------------------------------------------------
#   Copyright (C): MedAustron GmbH, ACMIT Gmbh and Medical University Vienna
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE for further details
# -----------------------------------------------------------------------------

"""
Compare two 3D images using the gamma index formalism as introduced by Daniel Low (1998).
"""

import numpy as np
import itk
import logging

logger = logging.getLogger(__name__)


def _reldiff2(dref, dtarget, ddref):
    """
    Convenience function for implementation of the following functions.
    The arguments `dref` and `dtarget` maybe scalars or arrays.
    The calling code is responsible for avoiding division by zero (make sure that ddref>0).
    """
    ddiff = dtarget - dref
    reldd2 = (ddiff / ddref) ** 2
    return reldd2


def get_gamma_index(ref, target, **kwargs):
    """
    Compare two 3D images using the gamma index formalism as introduced by Daniel Low (1998).
    The positional arguments 'ref' and 'target' should behave like ITK image objects.
    Possible keyword arguments include:
    * `dd` indicates "dose difference" scale as a relative value, in units of percent (the dd value is this percentage of the max dose in the reference image)
    * `ddpercent` is a flag, True (default) means that dd is given in percent, False means that dd is absolute.
    * `dta` indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * `threshold` indicates minimum dose value (exclusive) for calculating gamma values
    * `verbose` is a flag, True will result in some chatter, False will keep the computation quiet.
    * `threshold_percent` is a flag, True means that threshold is given in percent, False (default) means that the threshold is absolute.

    Returns an image with the same geometry as the target image.
    For all target voxels in the overlap between ref and target that have d>dmin, a gamma index value is given.
    For all other voxels the "defvalue" is given.
    TODO: allow 2D images, by creating 3D images with a 1-bin Z dimension. Should be very easy.
    The 3D gamma image computed using these "fake 3D" images can then be collapsed back to a 2D image.
    """
    if (
        (np.allclose(ref.GetOrigin(), target.GetOrigin()))
        and (np.allclose(ref.GetSpacing(), target.GetSpacing()))
        and (
            ref.GetLargestPossibleRegion().GetSize()
            == ref.GetLargestPossibleRegion().GetSize()
        )
    ):
        if kwargs.get("verbose", False):
            print(
                "Images with equal geometry, using the slightly faster implementation."
            )
        return gamma_index_3d_equal_geometry(ref, target, **kwargs)
    else:
        if kwargs.get("verbose", False):
            print(
                "Images with different geometry, using the slightly slower implementation."
            )
        return gamma_index_3d_unequal_geometry(ref, target, **kwargs)


# FIXME: Should this function remain public or be made private (by prefixing it with an _underscore)?
# TODO: Discuss whether to keep this function. It is 30% faster than the
# "unequal geometry" implementation on the same input images. Is that worth it?
def gamma_index_3d_equal_geometry(
    imgref,
    imgtarget,
    dta=3.0,
    dd=3.0,
    ddpercent=True,
    threshold=0.0,
    defvalue=-1.0,
    verbose=False,
    threshold_percent=False,
):
    """
    Compare two images with equal geometry, using the gamma index formalism as introduced by Daniel Low (1998).
    * ddpercent indicates "dose difference" scale as a relative value, in units percent (the dd value is this percentage of the max dose in the reference image)
    * ddabs indicates "dose difference" scale as an absolute value
    * dta indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * threshold indicates minimum dose value (exclusive) for calculating gamma values: target voxels with dose<=threshold are skipped and get assigned gamma=defvalue.
    * threshold_percent is a flag, True means that threshold is given in percent, False (default) means that the threshold is absolute.
    Returns an image with the same geometry as the target image.
    For all target voxels that have d>threshold, a gamma index value is given.
    For all other voxels the "defvalue" is given.
    If geometries of the input images are not equal, then a `ValueError` is raised.
    """
    aref = itk.GetArrayViewFromImage(imgref).swapaxes(0, 2)
    atarget = itk.GetArrayViewFromImage(imgtarget).swapaxes(0, 2)
    if aref.shape != atarget.shape:
        raise ValueError(
            "input images have different geometries ({} vs {} voxels)".format(
                aref.shape, atarget.shape
            )
        )
    if not np.allclose(imgref.GetSpacing(), imgtarget.GetSpacing()):
        raise ValueError(
            "input images have different geometries ({} vs {} spacing)".format(
                imgref.GetSpacing(), imgtarget.GetSpacing()
            )
        )
    if not np.allclose(imgref.GetOrigin(), imgtarget.GetOrigin()):
        raise ValueError(
            "input images have different geometries ({} vs {} origin)".format(
                imgref.GetOrigin(), imgtarget.GetOrigin()
            )
        )
    if ddpercent:
        dd *= 0.01 * np.max(aref)
    if threshold_percent:
        threshold *= 0.01 * np.max(aref)
    relspacing = np.array(imgref.GetSpacing(), dtype=float) / dta
    inv_spacing = np.ones(3, dtype=float) / relspacing
    g00 = np.ones(aref.shape, dtype=float) * -1
    mask = atarget > threshold
    g00[mask] = np.sqrt(_reldiff2(aref[mask], atarget[mask], dd))
    nx, ny, nz = atarget.shape
    ntot = nx * ny * nz
    nmask = np.sum(mask)
    ndone = 0
    if verbose:
        print("Both images have {} x {} x {} = {} voxels.".format(nx, ny, nz, ntot))
        print("{} target voxels have a dose > {}.".format(nmask, threshold))
    g2 = np.zeros((nx, ny, nz), dtype=float)
    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                if g00[x, y, z] < 0:
                    continue
                igmax = np.round(g00[x, y, z] * inv_spacing).astype(
                    int
                )  # maybe we should use "floor" instead of "round"
                if (igmax == 0).all():
                    g2[x, y, z] = g00[x, y, z] ** 2
                else:
                    ixmin = max(x - igmax[0], 0)
                    ixmax = min(x + igmax[0] + 1, nx)
                    iymin = max(y - igmax[1], 0)
                    iymax = min(y + igmax[1] + 1, ny)
                    izmin = max(z - igmax[2], 0)
                    izmax = min(z + igmax[2] + 1, nz)
                    ix, iy, iz = np.meshgrid(
                        np.arange(ixmin, ixmax),
                        np.arange(iymin, iymax),
                        np.arange(izmin, izmax),
                        indexing="ij",
                    )
                    g2mesh = _reldiff2(aref[ix, iy, iz], atarget[x, y, z], dd)
                    g2mesh += ((relspacing[0] * (ix - x))) ** 2
                    g2mesh += ((relspacing[1] * (iy - y))) ** 2
                    g2mesh += ((relspacing[2] * (iz - z))) ** 2
                    g2[x, y, z] = np.min(g2mesh)
                ndone += 1
                if verbose and ((ndone % 1000) == 0):
                    print("{0:.1f}% done...\r".format(ndone * 100.0 / nmask), end="")
    g = np.sqrt(g2)
    g[np.logical_not(mask)] = defvalue
    # ITK does not support double precision images by default => cast down to float32.
    # Also: only the first few digits of gamma index values are interesting.
    gimg = itk.GetImageFromArray(g.swapaxes(0, 2).astype(np.float32).copy())
    gimg.CopyInformation(imgtarget)
    if verbose:
        print("100% done!     ")
    return gimg


# FIXME: should this function remain public or be made private (by prefixing it with an _underscore)?
def gamma_index_3d_unequal_geometry(
    imgref,
    imgtarget,
    dta=3.0,
    dd=3.0,
    ddpercent=True,
    threshold=0.0,
    defvalue=-1.0,
    verbose=False,
    threshold_percent=False,
):
    """
    Compare 3-dimensional arrays with possibly different spacing and different origin, using the
    gamma index formalism, popular in medical physics.
    We assume that the meshes are *NOT* rotated w.r.t. each other.
    * `dd` indicates by default the "dose difference" scale as a relative value, in units percent (the dd value is this percentage of the max dose in the reference image).
    * If `ddpercent` is False, then dd is taken as an absolute value.
    * `dta` indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * `threshold` indicates minimum dose value (exclusive) for calculating gamma values
    * `threshold_percent` is a flag, True means that threshold is given in percent, False (default) means that the threshold is absolute.

    Returns an image with the same geometry as the target image.
    For all target voxels that are in the overlap region with the refernce image and that have d>threshold,
    a gamma index value is given. For all other voxels the "defvalue" is given.
    """
    # get arrays
    aref = itk.GetArrayViewFromImage(imgref).swapaxes(0, 2)
    atarget = itk.GetArrayViewFromImage(imgtarget).swapaxes(0, 2)
    if ddpercent:
        dd *= 0.01 * np.max(aref)
    if threshold_percent:
        threshold *= 0.01 * np.max(aref)
    # test consistency: both must be 3D
    # it would be cool to make this for 2D as well (and D>3), but not now
    if len(aref.shape) != 3 or len(atarget.shape) != 3:
        return None
    # bbref  = bounding_box(imgref)
    # bbtarget = bounding_box(imgtarget)
    areforigin = np.array(imgref.GetOrigin())
    arefspacing = np.array(imgref.GetSpacing())
    atargetorigin = np.array(imgtarget.GetOrigin())
    atargetspacing = np.array(imgtarget.GetSpacing())
    nx, ny, nz = atarget.shape
    mx, my, mz = aref.shape
    ntot = nx * ny * nz
    mtot = mx * my * mz
    dta2 = dta**2
    mask = atarget > threshold
    nmask = np.sum(mask)
    if nmask == 0:
        print("WARNING: target has no dose over threshold.")
        dummy = itk.GetImageFromArray(
            (np.ones(atarget.shape) * defvalue).swapaxes(0, 2).copy()
        )
        dummy.CopyInformation(imgtarget)
        return dummy
    # now define the indices of the target image voxel centers
    ixtarget, iytarget, iztarget = np.meshgrid(
        np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij"
    )
    xtarget = atargetorigin[0] + ixtarget * atargetspacing[0]
    ytarget = atargetorigin[1] + iytarget * atargetspacing[1]
    ztarget = atargetorigin[2] + iztarget * atargetspacing[2]
    # indices ref image voxel centers that are closest to the target image voxel centers
    ixref = np.round((xtarget - areforigin[0]) / arefspacing[0]).astype(int)
    iyref = np.round((ytarget - areforigin[1]) / arefspacing[1]).astype(int)
    izref = np.round((ztarget - areforigin[2]) / arefspacing[2]).astype(int)
    # keep within range
    overlap = (
        (ixref >= 0)
        * (iyref >= 0)
        * (izref >= 0)
        * (ixref < mx)
        * (iyref < my)
        * (izref < mz)
    )
    mask *= overlap
    noverlap = np.sum(overlap)
    nmask = np.sum(mask)
    if nmask == 0:
        print("WARNING: images do not seem to overlap.")
        dummy = itk.GetImageFromArray(
            (np.ones(atarget.shape) * defvalue).swapaxes(0, 2).copy()
        )
        dummy.CopyInformation(imgtarget)
        return dummy
    if verbose:
        print("Reference image has {} x {} x {} = {} voxels.".format(mx, my, mz, mtot))
        print("Target image has {} x {} x {} = {} voxels.".format(nx, ny, nz, ntot))
        print(
            "{} target voxels are in the intersection of target and reference image.".format(
                noverlap
            )
        )
        print("{} of these have dose > {}.".format(nmask, threshold))
    ndone = 0
    # grid of "close points" in reference image
    xref = areforigin[0] + ixref * arefspacing[0]
    yref = areforigin[1] + iyref * arefspacing[1]
    zref = areforigin[2] + izref * arefspacing[2]
    # get a gamma value on this closest point
    gclose2 = np.zeros([nx, ny, nz], dtype=float)
    gclose2[mask] = (
        _reldiff2(aref[ixref[mask], iyref[mask], izref[mask]], atarget[mask], dd)
        + (
            (xtarget[mask] - xref[mask]) ** 2
            + (ytarget[mask] - yref[mask]) ** 2
            + (ztarget[mask] - zref[mask]) ** 2
        )
        / dta2
    )
    gclose = np.array(np.sqrt(gclose2))
    # igclose = np.array(np.ceil(np.sqrt(gclose2)),dtype=int)
    g2 = np.zeros([nx, ny, nz], dtype=float)
    # print("going to loop over {} voxels with large enough dose in reference image".format(np.sum(mask)))
    for mixref, miyref, mizref, mixtarget, miytarget, miztarget, mgclose in zip(
        ixref[mask],
        iyref[mask],
        izref[mask],
        ixtarget[mask],
        iytarget[mask],
        iztarget[mask],
        gclose[mask],
    ):
        # dtarget = atarget[mixtarget,miytarget,miztarget]
        # dref = aref[mixref,miyref,mizref]
        ixyztarget = np.array((mixtarget, miytarget, miztarget))
        ixyzref = np.array((mixref, miyref, mizref))
        targetpos = atargetorigin + ixyztarget * atargetspacing
        refpos = areforigin + ixyzref * arefspacing
        dixyz = np.floor(mgclose * dta / arefspacing).astype(int)  # or round, or ceil?
        imax = np.minimum(ixyzref + dixyz + 1, (mx, my, mz))
        imin = np.maximum(ixyzref - dixyz, (0, 0, 0))
        mixnear, miynear, miznear = np.meshgrid(
            np.arange(imin[0], imax[0]),
            np.arange(imin[1], imax[1]),
            np.arange(imin[2], imax[2]),
            indexing="ij",
        )
        g2near = _reldiff2(
            aref[mixnear, miynear, miznear],
            atarget[mixtarget, miytarget, miztarget],
            dd,
        )
        g2near += (areforigin[0] + mixnear * arefspacing[0] - targetpos[0]) ** 2 / dta2
        g2near += (areforigin[1] + miynear * arefspacing[1] - targetpos[1]) ** 2 / dta2
        g2near += (areforigin[2] + miznear * arefspacing[2] - targetpos[2]) ** 2 / dta2
        g2[mixtarget, miytarget, miztarget] = np.min(g2near)
        ndone += 1
        if verbose and ((ndone % 1000) == 0):
            print("{0:.1f}% done...\r".format(ndone * 100.0 / nmask), end="")
    g = np.sqrt(g2)
    g[np.logical_not(mask)] = defvalue
    # ITK does not support double precision images by default => cast down to float32.
    # Also: only the first few digits of gamma index values are interesting.
    gimg = itk.GetImageFromArray(g.swapaxes(0, 2).astype(np.float32).copy())
    gimg.CopyInformation(imgtarget)
    if verbose:
        print("100% done!     ")
    return gimg


#####################################################################################
# TODO: include the unit test in implementation (like here), or have it in a separate test directory?
#####################################################################################
import unittest
import sys
from datetime import datetime


class Test_GammaIndex3dIdenticalMesh(unittest.TestCase):
    def test_identity(self):
        # two identical images should give gamma=0.0 in all voxels
        # print("test identity")
        print("Test_GammaIndex3dIdenticalMesh test_identity")
        np.random.seed(1234567)
        a_rnd = np.random.uniform(0.0, 10.0, (4, 5, 6))
        img1 = itk.GetImageFromArray(a_rnd)
        img2 = itk.GetImageFromArray(a_rnd)
        img_gamma = gamma_index_3d_equal_geometry(img1, img2, dd=3.0, dta=2.0)
        self.assertTrue((itk.GetArrayViewFromImage(img_gamma) == 0.0).all())
        # print("DONE test identity")

    def test_scaling(self):
        # print("test scaling small")
        # two images identical up to a scaling factor 1.03 should give gamma(3%)<=1.0 in all voxels
        print("Test_GammaIndex3dIdenticalMesh test_scaling")
        np.random.seed(1234567)
        a_rnd = np.random.uniform(0.0, 10.0, (4, 5, 6))
        img1 = itk.GetImageFromArray(a_rnd)
        img2 = itk.GetImageFromArray(1.03 * a_rnd)
        img_gamma = gamma_index_3d_equal_geometry(img1, img2, dd=3.0, dta=2.0)
        self.assertTrue((itk.GetArrayViewFromImage(img_gamma) < 1.0001).all())
        # print("DONE test scaling")

    def test_checkerboards(self):
        # print("test 3D checkerboards: have D=0.25 in even voxels and D=0.75 in odd voxels for ref image, vice versa for test image.")
        # for every voxel in the target image, the neighboring voxels in the ref image has the same dose
        # therefore the gamma index should be equal to spacing/dta for all voxels.
        print("Test_GammaIndex3dIdenticalMesh test_checkerboards")
        nx, ny, nz = 4, 5, 6
        ix, iy, iz = np.meshgrid(
            np.arange(nx, dtype=int),
            np.arange(ny, dtype=int),
            np.arange(nz, dtype=int),
            indexing="ij",
        )
        a_odd = 0.5 * (((ix + iy + iz) % 2) == 1).astype(float) + 0.25
        a_even = 0.5 * (((ix + iy + iz) % 2) == 0).astype(float) + 0.25
        img_odd = itk.GetImageFromArray(a_odd)
        img_even = itk.GetImageFromArray(a_even)
        img_gamma_even_odd = gamma_index_3d_equal_geometry(
            img_even, img_odd, dd=10.0, dta=2.0
        )
        img_gamma_odd_even = gamma_index_3d_equal_geometry(
            img_odd, img_even, dd=10.0, dta=2.0
        )
        self.assertTrue(
            np.allclose(
                itk.GetArrayViewFromImage(img_gamma_odd_even),
                itk.GetArrayViewFromImage(img_gamma_even_odd),
            )
        )
        self.assertTrue(np.allclose(itk.GetArrayViewFromImage(img_gamma_odd_even), 0.5))
        # print("DONE test checkerboards")

    def test_large_image(self):
        print("Test_GammaIndex3dIdenticalMesh test_large_image")
        for N in [1, 2, 5, 10, 20]:
            # for N in [1,2,5,10,20,50]:
            # for N in [1,2,5,10,20,50,100]:
            tgen = datetime.now()
            img_ref = itk.GetImageFromArray(np.ones((N, N, N), dtype=float))
            img_target = itk.GetImageFromArray(np.random.normal(1.0, 0.02, (N, N, N)))
            tbefore = datetime.now()
            # print("{}^3 voxels generating images took {}".format(N,tbefore-tgen))
            img_NNN_gamma = gamma_index_3d_equal_geometry(
                img_ref, img_target, dd=2.0, dta=2.0
            )
            tafter = datetime.now()
            print("{}^3 voxels calculating gamma took {}".format(N, tafter - tbefore))


class Test_GammaIndex3dUnequalMesh(unittest.TestCase):
    def test_EqualMesh(self):
        # For equal meshes, the "unequalmesh" implementation should give the
        # same results as "equal mesh" implementation.
        print("Test_GammaIndex3dUnequalMesh test_EqualMesh")
        np.random.seed(71234567)
        for i in range(5):
            # print("{}. comparing implementations with 'equal' and 'unequal' geometry assumptions".format(i))
            nxyz = np.random.randint(25, 35, 3)
            oxyz = np.random.uniform(-100.0, 100.0, 3)
            sxyz = np.random.uniform(0.5, 2.5, 3)
            img_ref = itk.GetImageFromArray(
                np.ones(nxyz, dtype=float).swapaxes(0, 2).copy()
            )
            img_ref.SetOrigin(oxyz)
            img_ref.SetSpacing(sxyz)
            img_target = itk.GetImageFromArray(
                np.random.normal(1.0, 0.05, nxyz).swapaxes(0, 2).copy()
            )
            img_target.SetOrigin(oxyz)
            img_target.SetSpacing(sxyz)
            t0 = datetime.now()
            img_gamma_equal = gamma_index_3d_equal_geometry(
                img_ref, img_target, dd=3.0, dta=2.0
            )
            t1 = datetime.now()
            print(
                "{}. equal implementation with {} voxels took {}".format(
                    i, np.prod(nxyz), t1 - t0
                )
            )
            img_gamma_unequal = gamma_index_3d_unequal_geometry(
                img_ref, img_target, dd=3.0, dta=2.0
            )
            t2 = datetime.now()
            print(
                "{}. unequal implementation with {} voxels took {}".format(
                    i, np.prod(nxyz), t2 - t1
                )
            )
            aeq = itk.GetArrayViewFromImage(img_gamma_equal)
            auneq = itk.GetArrayViewFromImage(img_gamma_unequal)
            # print("eq min/median/mean/max={}/{}/{}/{}".format(np.min(aeq),np.median(aeq),np.mean(aeq),np.max(aeq)))
            # print("uneq min/median/mean/max={}/{}/{}/{}".format(np.min(auneq),np.median(auneq),np.mean(auneq),np.max(auneq)))
            # print("{} out of {} are close".format(np.sum(np.isclose(aeq,auneq)),np.prod(aeq.shape)))
            # print("eq first 2x2x2: {}".format(aeq[:2,:2,:2]))
            # print("uneq first 2x2x2: {}".format(auneq[:2,:2,:2]))
            # print("eq last 2x2x2: {}".format(aeq[-2:,-2:,-2:]))
            # print("uneq last 2x2x2: {}".format(auneq[-2:,-2:,-2:]))
            self.assertTrue(np.allclose(aeq, auneq))
            print("Yay!")

    def test_Shift(self):
        # two images identical up to a translation less than half the spacing should yield a gamma index
        # equal to the ratio of the length of the translation vector and the DTA.
        print("Test_GammaIndex3dUnequalMesh test_Shift")
        np.random.seed(1234568)
        for i in range(5):
            # print("shift image no. {}".format(i))
            nxyz = np.random.randint(5, 15, 3)
            oxyz = np.random.uniform(-100.0, 100.0, 3)
            sxyz = np.random.uniform(0.5, 2.5, 3)
            txyz = np.random.uniform(-0.5, 0.5, 3) * sxyz
            data = np.random.normal(1.0, 0.1, nxyz)
            img_ref = itk.GetImageFromArray(data.swapaxes(0, 2).copy())
            img_ref.SetSpacing(sxyz)
            img_ref.SetOrigin(oxyz)
            img_target = itk.GetImageFromArray(
                data.swapaxes(0, 2).copy()
            )  # same as ref
            img_target.SetSpacing(sxyz)  # same as ref
            img_target.SetOrigin(oxyz + txyz)  # translated!
            ddp = 3.0  # %
            dta = 2.0  # mm
            img_gamma = gamma_index_3d_unequal_geometry(
                img_ref, img_target, dd=ddp, dta=dta
            )
            agamma = itk.GetArrayViewFromImage(img_gamma).swapaxes(0, 2)
            gval_expected = np.sqrt(np.sum((txyz / dta) ** 2))
            self.assertTrue(np.allclose(agamma, gval_expected))
            # print("ok #voxels={} gval_exp={}".format(np.prod(nxyz),gval_expected) )

    def test_Gradient(self):
        # Let ref and target be two 3D images that are effectively 1D images (only vary in X)
        # and ref has a much smaller spacing, but its volume includes the target volume.
        # Now it's easy to compute 'by hand' the min(gamma(i,j)) for each target voxel.
        # This tests that the gamma calculation is done correctly wehn it needs
        # to "travel" more than one voxel to get to the "minimum".
        print("Test_GammaIndex3dUnequalMesh test_Gradient")
        refN = (100, 10, 10)
        refO = (-50.0, 0.0, 0.0)
        refS = (1.0, 1.0, 1.0)
        ixref, iyref, izref = np.meshgrid(
            np.arange(refN[0]), np.arange(refN[1]), np.arange(refN[2]), indexing="ij"
        )
        # print("ixref shape is {}".format(ixref.shape))
        targetN = (10, 3, 3)
        ixtarget, iytarget, iztarget = np.meshgrid(
            np.arange(targetN[0]),
            np.arange(targetN[1]),
            np.arange(targetN[2]),
            indexing="ij",
        )
        np.random.seed(1234569)
        for i in range(5):
            # print("{}th gradient test".format(i))
            ###################
            # generate random REF data
            ###################
            refGRAD = np.random.uniform(-1.0, 1.0)
            refDATA = ixref * refGRAD
            refDATA += 0.5 - np.min(refDATA)  # ensure that all dose values are positive
            refOFFSET = refDATA[0, 0, 0]
            img_ref = itk.GetImageFromArray(refDATA.swapaxes(0, 2).copy())
            img_ref.SetSpacing(refS)
            img_ref.SetOrigin(refO)
            ######################
            # generate random TARGET data
            ######################
            # random offset in x (but less than reference spacing)
            targetO = np.random.uniform(-0.5, 0.5, 3)
            # random x spacing, larger than reference but make sure to stay within ref volume
            sx = np.random.uniform(1.5, 2.0)
            targetS = (sx, 3.0, 3.0)
            targetGRAD = np.random.uniform(-10.0, 10.0)
            targetDATA = ixtarget * targetGRAD
            targetDATA += 0.5 - np.min(
                targetDATA
            )  # ensure that all dose values are positive
            targetOFFSET = targetDATA[0, 0, 0]
            img_target = itk.GetImageFromArray(targetDATA.swapaxes(0, 2).copy())
            img_target.SetSpacing(targetS)
            img_target.SetOrigin(targetO)
            #####################################
            # loop over range of gamma parameters
            #####################################
            for ddp in np.arange(1.0, 5.001):
                for dta in np.arange(1.0, 5.001):
                    ##########################
                    # calculate expected gamma
                    ##########################
                    ix, iy = np.meshgrid(
                        np.arange(targetN[0]), np.arange(refN[0]), indexing="ij"
                    )
                    dr2 = (targetO[0] + ix * targetS[0] - refO[0] - iy * refS[0]) ** 2
                    dr2 += np.sum(targetO[1:] ** 2)
                    dr2 /= dta**2
                    ddref2 = (np.max(refDATA) * ddp * 0.01) ** 2
                    dd2 = (
                        targetOFFSET + targetGRAD * ix - refGRAD * iy - refOFFSET
                    ) ** 2 / ddref2
                    # find minimum and take sqrt
                    gamma_1d = np.sqrt(np.min(dd2 + dr2, axis=1))
                    # copy to 3d
                    gamma_all = np.zeros(targetN, dtype=float)
                    gamma_all[ixtarget, iytarget, iztarget] = gamma_1d[ixtarget]
                    #################################################
                    # calculate gamma gamma_index_3d_unequal_geometry
                    #################################################
                    img_gamma = gamma_index_3d_unequal_geometry(
                        img_ref, img_target, dd=ddp, dta=dta
                    )
                    # print(type(img_gamma))
                    agamma = itk.GetArrayViewFromImage(img_gamma).swapaxes(0, 2)
                    # for jx in range(targetN[0]):
                    #    print("{} {}".format(gamma_1d[jx],agamma[jx,0,0]))
                    self.assertTrue(np.allclose(agamma, gamma_all))
                    # print("ok ddp={} dta={} refGRAD={} targetGRAD={}".format(ddp,dta,refGRAD,targetGRAD))
            # print("{}th gradient test finished".format(i))


# vim: set et softtabstop=4 sw=4 smartindent:
