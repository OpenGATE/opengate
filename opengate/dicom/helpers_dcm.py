#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

assert sys.version_info.major == 3
import os
from pydicom.dataset import FileDataset, FileMetaDataset, Dataset
from pydicom.sequence import Sequence
from pydicom.uid import UID
import pydicom
import itk
import numpy as np
from datetime import datetime
import opengate as gate
from scipy.interpolate import RegularGridInterpolator


def compare_dose_at_points(plan_dose_obj, structs_obj, sim_dose_resampled):
    rd = plan_dose_obj.dicom_obj
    plan_dose_image = plan_dose_obj.image
    img_plan = itk.GetArrayViewFromImage(plan_dose_image)
    # get dose grid scaling
    DoseGridScalingFactor = rd.DoseGridScaling
    # get max dose plan
    max_dose = DoseGridScalingFactor * np.amax(img_plan)
    abs_thresh = 0.01 * max_dose  # 1% max dose

    # get points from plan
    ref_points = get_reference_points(structs_obj.structure_set)

    # get planned dose for points
    planned_doses = get_dose_from_points(
        plan_dose_image, ref_points, DoseGridScalingFactor
    )

    # get simulated dose
    sim_doses = get_dose_from_points(
        sim_dose_resampled, ref_points, DoseGridScalingFactor
    )

    # get difference
    diff_doses = sim_doses - planned_doses
    print(diff_doses)
    print(f"{abs_thresh = }")
    print(f"mean diff = {np.mean(abs(diff_doses))}")

    ok = np.mean(abs(diff_doses)) < abs_thresh

    return ok


def test_gamma_index(ref, target, pass_rate=0.95, **kwargs):
    perc_pass = gamma_pass_rate(ref, target, **kwargs)
    print(f"gamma index: {perc_pass}")
    ok = False
    if perc_pass >= pass_rate:
        ok = True

    return ok, perc_pass


def gamma_pass_rate(ref, target, **kwargs):
    img_gamma = gate.get_gamma_index(ref, target, **kwargs)
    img_gamma_np = itk.GetArrayViewFromImage(img_gamma)
    L_nonNeg = img_gamma_np >= 0
    gamma_ind_sum = np.sum(img_gamma_np[L_nonNeg] < 1.000000001)
    gamma_ind_pass_rate_actual = gamma_ind_sum / np.sum(L_nonNeg)
    return gamma_ind_pass_rate_actual


def get_dose_from_points(dose_img, points, DoseGridScalingFactor):
    # get doses
    doses = []
    for pt in points:
        dose = float(returnValueAtPosition(dose_img, pt, True) * DoseGridScalingFactor)
        doses.append(dose)

    return np.array(doses)


def get_reference_points(rs):
    # get coordinates of points from TPS (in Patient Coordinate System)
    ref_points = []

    for contour in rs.ROIContourSequence:
        if contour.ContourSequence[0].ContourGeometricType != "POINT":
            continue
        pt = contour.ContourSequence[0].ContourData
        ref_points.append(pt)

    return np.array(ref_points)


def returnValueAtPosition(img, pointOfInterest=[1, 1, 1], interpolate=True):
    if interpolate:
        # extract continous index for physical coordinate
        indexToLookUp = img.TransformPhysicalPointToContinuousIndex(pointOfInterest)

    # flip index to align it with numpy conventions
    # flip=indexToLookUp[::-1]
    # convert to list
    indexToLookUpAsList = [
        indexToLookUp[2],
        indexToLookUp[1],
        indexToLookUp[0],
    ]  # list(flip)

    # numpy data array from image
    nda = itk.GetArrayFromImage(img)

    # generate indices for interpolation file, 0 to size for all dimensions
    x = np.arange(0, nda.shape[0], 1)
    y = np.arange(0, nda.shape[1], 1)
    z = np.arange(0, nda.shape[2], 1)

    # initialize interpolation function
    my_interpolating_function = RegularGridInterpolator((x, y, z), nda)

    pts = np.array(indexToLookUpAsList)
    foundValue = my_interpolating_function(pts)

    return foundValue


class bounding_box(object):
    """
    Define ranges in which things are in 3D space.
    Maybe this should be more dimensionally flexible, to also handle 2D or N
    dimensional bounding boxes.
    """

    def __init__(self, **kwargs):
        """
        Initialize using *one* of the following kwargs:
        * 'bb': copy from another bounding_box object
        * 'img': obtain bounding box from a 'itk' image
        * 'xyz': initialize bounding box with 6 floats, shaped (x1,y1,z1,x2,y2,z2),
          ((x1,x2),(y1,y2),(z1,z2)) or ((x1,y1,z1),(x2,y2,z2)).
        TODO: maybe 'extent' would be a better name for the "limits" data member.
        TODO: maybe the different kind of constructors should be implemented as static methods instead of with kwargs.
        """
        nkeys = len(kwargs.keys())
        self.limits = np.empty((3, 2))
        if nkeys == 0:
            self.reset()
        elif nkeys > 1:
            raise RuntimeError(
                "too many arguments ({}) to bounding box constructor: {}".format(
                    nkeys, kwargs
                )
            )
        elif "bb" in kwargs:
            bb = kwargs["bb"]
            self.limits = np.copy(bb.limits)
        elif "img" in kwargs:
            img = kwargs["img"]
            if len(img.GetOrigin()) != 3:
                raise ValueError("only 3D bounding boxes/images are supported")
            origin = np.array(img.GetOrigin())
            spacing = np.array(img.GetSpacing())
            dims = np.array(img.GetLargestPossibleRegion().GetSize())
            self.limits[:, 0] = origin - 0.5 * spacing
            self.limits[:, 1] = origin + (dims - 0.5) * spacing
        elif "xyz" in kwargs:
            xyz = np.array(kwargs["xyz"], dtype=float)
            if xyz.shape == (3, 2):
                self.limits = xyz
            elif xyz.shape == (2, 3):
                self.limits = xyz.T
            elif xyz.shape == (6,):
                self.limits = xyz.reshape(3, 2)
            else:
                raise ValueError(
                    "unsupported shape for xyz limits: {}".format(xyz.shape)
                )
            if np.logical_not(self.limits[:, 0] <= self.limits[:, 1]).any():
                raise ValueError(
                    "min should be less or equal max but I got min={} max={}".format(
                        self.limits[:, 0], self.limits[:, 1]
                    )
                )

    def reset(self):
        self.limits[:, 0] = np.inf
        self.limits[:, 1] = -np.inf

    def __repr__(self):
        return "bounding box [[{},{}],[{},{}],[{},{}]]".format(
            *(self.limits.flat[:].tolist())
        )

    @property
    def volume(self):
        if np.isinf(self.limits).any():
            return 0.0
        return np.prod(np.diff(self.limits, axis=1))

    @property
    def empty(self):
        return self.volume == 0.0

    def __eq__(self, rhs):
        if self.empty and rhs.empty:
            return True
        return (self.limits == rhs.limits).all()

    def should_contain(self, point):
        apoint = np.array(point, dtype=float)
        assert len(apoint.shape) == 1
        assert apoint.shape[0] == 3
        self.limits[:, 0] = np.min([self.limits[:, 0], apoint], axis=0)
        self.limits[:, 1] = np.max([self.limits[:, 1], apoint], axis=0)

    def should_contain_all(self, points):
        assert np.array(points).shape[1] == 3
        self.should_contain(np.min(points, axis=0))
        self.should_contain(np.max(points, axis=0))

    @property
    def mincorner(self):
        return self.limits[:, 0]

    @property
    def maxcorner(self):
        return self.limits[:, 1]

    @property
    def center(self):
        return 0.5 * (self.mincorner + self.maxcorner)

    def contains(self, point, inner=False, rtol=0.0, atol=1e-3):
        assert len(point) == 3
        apoint = np.array(point)
        if inner:
            # really inside, NOT at the boundary (within rounding errors)
            gt_lo_lim = np.logical_not(
                np.isclose(self.limits[:, 0], apoint, rtol=rtol, atol=atol)
            ) * (apoint > self.limits[:, 0])
            lt_up_lim = np.logical_not(
                np.isclose(self.limits[:, 1], apoint, rtol=rtol, atol=atol)
            ) * (apoint < self.limits[:, 1])
            return (gt_lo_lim * lt_up_lim).all()
        else:
            # inside, or at the boundary (within rounding errors)
            ge_lo_lim = np.isclose(self.limits[:, 0], apoint, rtol=rtol, atol=atol) | (
                apoint > self.limits[:, 0]
            )
            le_up_lim = np.isclose(self.limits[:, 1], apoint, rtol=rtol, atol=atol) | (
                apoint < self.limits[:, 1]
            )
            return (ge_lo_lim * le_up_lim).all()

    def encloses(self, bb, inner=False, rtol=0.0, atol=1e-3):
        return self.contains(bb.mincorner, inner) and self.contains(bb.maxcorner, inner)

    def __contains__(self, item):
        """
        Support for the 'in' operator

        Works only for other bounding boxes, and for 3D points represented by numpy arrays of shape (3,).
        """
        if type(item) == type(self):
            return self.encloses(item)
        else:
            return self.contains(item)

    def add_margins(self, margins):
        # works both with scalar and vector
        # TODO: allow negative margins, but implement appropriate behavior in case margin is larger than the bb.
        self.limits[:, 0] -= margins
        self.limits[:, 1] += margins

    def merge(self, bb):
        if self.empty:
            self.limits = np.copy(bb.limits)
        elif not bb.empty:
            self.should_contain(bb.mincorner)
            self.should_contain(bb.maxcorner)

    def have_overlap(self, bb):
        # not sure this is correct!
        return (
            (not self.empty)
            and (not bb.empty)
            and (self.limits[:, 0] <= bb.limits[:, 1]).all()
            and (bb.limits[:, 0] <= self.limits[:, 1]).all()
        )

    def intersect(self, bb):
        if not self.have_overlap(bb):
            self.reset()
        else:
            self.limits[:, 0] = np.max([self.mincorner, bb.mincorner], axis=0)
            self.limits[:, 1] = np.min([self.maxcorner, bb.maxcorner], axis=0)

    def indices_in_image(self, img, rtol=0.0, atol=1e-3):
        """
        Determine the voxel indices of the bounding box corners in a given image.

        In case the corners are within rounding margin (given by `eps`) on a
        boundary between voxels in the image, then voxels that would only have
        an infinitesimal intersection with the bounding box are not included.
        The parameters `atol` and `rtol` are used to determine with
        `np.isclose` if BB corners are on a voxel boundary. In case the BB
        corners are outside of the image volume, the indices will be out of the
        range (negative, of larger than image size).

        Returns two numpy arrays of size 3 and dtype int, representing the
        inclusive/exclusive image indices of the lower/upper corners,
        respectively.
        """
        # generically, this is what we want to do:
        bb_img = bounding_box(img=img)
        spacing = np.array(img.GetSpacing())
        ibbmin, devmin = np.divmod(self.mincorner - bb_img.mincorner, spacing)
        ibbmax, devmax = np.divmod(self.maxcorner - bb_img.mincorner, spacing)
        # but if we are "almost exactly" on a voxel boundary we need to be picky on which side to land
        below = np.isclose(devmin, spacing, rtol=rtol, atol=atol)
        above = devmax > atol
        ibbmin[below] += 1  # add one IF on a voxel boundary
        ibbmax[above] += 1  # add one UNLESS on a voxel boundary
        return np.int32(ibbmin), np.int32(ibbmax)

    @property
    def xmin(self):
        return self.limits[0, 0]

    @property
    def xmax(self):
        return self.limits[0, 1]

    @property
    def ymin(self):
        return self.limits[1, 0]

    @property
    def ymax(self):
        return self.limits[1, 1]

    @property
    def zmin(self):
        return self.limits[2, 0]

    @property
    def zmax(self):
        return self.limits[2, 1]


def resample_dose(dose, mass, newgrid):
    assert equal_geometry(dose, mass)
    if equal_geometry(dose, newgrid):
        # If input and output geometry are equal, then we don't need to do anything, just copy the input dose.
        newdose = itk.image_from_array(itk.array_from_image(dose))
        newdose.CopyInformation(dose)
        return newdose
    if not enclosing_geometry(dose, newgrid):
        # In a later release we may provide some smart code to deal with dose resampling outside of the input geometry.
        raise RuntimeError("new grid must be inside the old one")
    xol, yol, zol = [
        _overlaps(*xyz)
        for xyz in zip(
            dose.GetOrigin(),
            dose.GetSpacing(),
            dose.GetLargestPossibleRegion().GetSize(),
            newgrid.GetOrigin(),
            newgrid.GetSpacing(),
            newgrid.GetLargestPossibleRegion().GetSize(),
        )
    ]
    adose = itk.array_from_image(dose)
    amass = itk.array_from_image(mass)
    aedep = adose * amass
    # now the magic happens :-)
    anew = np.tensordot(
        zol,
        np.tensordot(yol, np.tensordot(xol, aedep, axes=(0, 2)), axes=(0, 2)),
        axes=(0, 2),
    )
    wsum = np.tensordot(
        zol,
        np.tensordot(yol, np.tensordot(xol, amass, axes=(0, 2)), axes=(0, 2)),
        axes=(0, 2),
    )
    # paranoia
    mzyx = tuple(np.array(newgrid.GetLargestPossibleRegion().GetSize())[::-1])
    assert anew.shape == tuple(mzyx)
    assert wsum.shape == tuple(mzyx)
    # dose=edep/mass, but only if mass>0
    mask = wsum > 0
    anew[mask] /= wsum[mask]
    newdose = itk.image_from_array(anew)
    newdose.CopyInformation(newgrid)

    return newdose


def crop_and_pad_image(input_img, from_index, to_index, hu_value_for_padding):
    """
    We would like to use itk.RegionOfInterestFilter but that filter does recalculate the origin correctly.
    So now we do this manually, through numpy.
    """
    # "crop and pad manually with numpy")
    aimg = itk.GetArrayViewFromImage(input_img)
    # ("got input image, the array view {} contiguous".format("IS" if aimg.flags.contiguous else "IS NOT"))

    if (from_index > 0).all() and (to_index <= np.array(aimg.shape[::-1])).all():
        # only cropping, no padding")
        return CropImageManuallyWithNumpy(input_img, from_index, to_index)

    # "both cropping and padding")
    atype = aimg.dtype.type
    asize = np.array(aimg.shape)[::-1]
    new_size = to_index - from_index
    # "old size: {} new size: {}".format(asize,new_size))
    from_old = np.array(
        [max(i, 0) for i in from_index]
    )  # i<0: padding, i>0: cropping; i==0: no change
    to_old = np.array(
        [min(s, j) for j, s in zip(to_index, asize)]
    )  # j>s: padding, j<s: cropping; j==s: no change
    from_new = np.array(
        [max(-i, 0) for i in from_index]
    )  # i<0: padding, i>0: cropping; i==0: no change
    to_new = np.array(
        [inew + jorig - iorig for inew, iorig, jorig in zip(from_new, from_old, to_old)]
    )
    # "from indices in orig: {}".format(from_old))
    # "to indices in orig: {}".format(to_old))
    # "from indices in output: {}".format(from_new))
    # "to indices in output: {}".format(to_new))
    assert (to_new <= new_size).all()
    assert (to_new - from_new == to_old - from_old).all()
    assert (to_new - from_new > 0).all()
    anew = np.full(new_size[::-1], fill_value=hu_value_for_padding, dtype=atype)
    # "new image array {} contiguous".format("IS" if anew.flags.contiguous else "IS NOT"))
    anew[
        from_new[2] : to_new[2], from_new[1] : to_new[1], from_new[0] : to_new[0]
    ] = aimg[from_old[2] : to_old[2], from_old[1] : to_old[1], from_old[0] : to_old[0]]
    # "new image array with shape {} is now filled".format(aimg.shape))
    new_img = itk.GetImageFromArray(anew)
    # "new image created from array, it has size {}".format(new_img.GetLargestPossibleRegion().GetSize()))
    # new_img.CopyInformation(input_img)
    spacing = np.array(input_img.GetSpacing())
    old_origin = np.array(input_img.GetOrigin())
    print(f"{old_origin=}")
    new_origin = old_origin + (from_index) * spacing
    print(f"{new_origin=}")
    new_img.SetSpacing(spacing)
    new_img.SetOrigin(new_origin)
    # "cropping and padding done, manually with numpy")
    return new_img


def CropImageManuallyWithNumpy(input_img, from_index, to_index):
    """
    We would like to use itk.RegionOfInterestImageFilter but that filter does not recalculate the origin correctly.
    So now we do this manually, through numpy.
    """
    aimg = itk.GetArrayViewFromImage(input_img)
    # "got input image, the array view {} contiguous".format("IS" if aimg.flags.contiguous else "IS NOT"))
    assert (from_index > 0).all()
    assert (to_index <= np.array(aimg.shape[::-1])).all()
    # ("going to create new image, forcing slice of old array to be continuous")
    new_img = itk.GetImageFromArray(
        np.ascontiguousarray(
            aimg[
                from_index[2] : to_index[2],
                from_index[1] : to_index[1],
                from_index[0] : to_index[0],
            ]
        )
    )
    # "going to assign spacing and origin to new image")
    # new_img.CopyInformation(input_img)
    spacing = np.array(input_img.GetSpacing())
    old_origin = np.array(input_img.GetOrigin())
    new_origin = old_origin + (from_index) * spacing
    new_img.SetSpacing(spacing)
    new_img.SetOrigin(new_origin)
    # "cropping done, manually with numpy")
    return new_img


def equal_geometry(img1, img2):
    """
    Do img1 and img2 have the same geometry (same voxels)?

    This is an auxiliary function for `mass_weighted_resampling`.
    """
    if not np.allclose(img1.GetOrigin(), img2.GetOrigin()):
        return False
    if not np.allclose(img1.GetSpacing(), img2.GetSpacing()):
        return False
    if (
        np.array(img1.GetLargestPossibleRegion().GetSize())
        == np.array(img2.GetLargestPossibleRegion().GetSize())
    ).all():
        return True
    return False


def enclosing_geometry(img1, img2):
    """
    Does img1 enclose img2?

    This function could be used to test whether img2 can be used as a reference image for resampling img1.
    """
    if equal_geometry(img1, img2):
        return True
    o1 = np.array(itk.origin(img1))
    o2 = np.array(itk.origin(img2))
    s1 = np.array(itk.spacing(img1))
    s2 = np.array(itk.spacing(img2))
    n1 = np.array(itk.size(img1))
    n2 = np.array(itk.size(img2))
    # compute corners
    lower1 = o1 - 0.5 * s1
    lower2 = o2 - 0.5 * s2
    upper1 = o1 + (n1 - 0.5) * s1
    upper2 = o2 + (n2 - 0.5) * s2

    # now check the lower corner
    if (np.logical_not(np.isclose(lower1, lower2)) * (lower1 > lower2)).any():
        return False
    # now check the upper corner
    if (np.logical_not(np.isclose(upper1, upper2)) * (upper1 < upper2)).any():
        return False
    return True


def _overlaps(a0, da, na, b0, db, nb, label="", center=True):
    """
    This function returns an (na,nb) array with the length of the overlaps in
    two ranges of intervals. In other words, the value of the element (i,j)
    represents the length that the i'th interval of A overlaps with the j'th
    interval of B.

    If center is True, then a0 and b0 are assumed to be the *centers* of the first
    interval of range A and B, respectively.
    If center is False, then a0 and b0 are assumed to be the *left edge* of the first
    interval of range A and B, respectively.

    This is an auxiliary function for `mass_weighted_resampling`.
    """
    # paranoid checks :-)
    assert da > 0
    assert db > 0
    assert type(na) == int
    assert type(nb) == int
    assert na > 0
    assert nb > 0
    assert a0 < np.inf
    assert b0 < np.inf
    assert a0 > -np.inf
    assert b0 > -np.inf
    if center:
        # Assume that the given a0 and b0 values represent the center of the first bin.
        # In these calculations it's more convenient to work with the left edge.
        a0 -= 0.5 * da
        b0 -= 0.5 * db
    o = np.zeros((na, nb), dtype=float)
    if a0 + na * da < b0 or b0 + nb * db < a0:
        # no overlap at all
        return o
    ia, a, ada = 0, a0, a0 + da
    ib, b, bdb = 0, b0, b0 + db
    while ia < na and ib < nb:
        if ada < b or np.isclose(ada, b):
            ab = True
        elif bdb < a or np.isclose(bdb, a):
            ab = False
        else:
            o[ia, ib] = min(ada, bdb) - max(a, b)
            # logger.debug(f"o[{ia},{ib}]={o[ia,ib]:.2f}")
            ab = ada < bdb
        if ab:
            ia += 1
            a = ada
            ada = a0 + (ia + 1) * da
        else:
            ib += 1
            b = bdb
            bdb = b0 + (ib + 1) * db
    return o


def create_mass_image(ct, hlut_path, overrides=dict()):
    """
    This function creates a mass image based on the HU values in a ct image, a
    Hounsfield-to-density lookup table and (optionally) a dictionary of
    override densities for specific HU values.

    If the HU-to-density lookup table has 2 columns, it is interpreted as a
    density curve that needs to be interpolated for the intermediate HU values.
    If the HU-to-density lookup table has 3 columns, then it is interpreted as
    a step-wise density table, with a constant density within each successive
    interval (no interpolation).
    """
    HLUT = np.loadtxt(hlut_path)
    # logger.debug("table shape is {}".format(HLUT.shape))
    # logger.debug("table data type is {}".format(HLUT.dtype))
    assert len(HLUT.shape) == 2, "HU lookup table has wrong dimension (should be 2D)"
    assert (
        HLUT.shape[1] // 2 == 1
    ), "HU lookup table has wrong number of columns (should be 2 or 3)"
    act = itk.GetArrayFromImage(ct)
    amass = np.zeros(act.shape, dtype=np.float32)
    done = np.zeros(act.shape, dtype=bool)
    if HLUT.shape[1] == 2:
        HU = HLUT[:, 0]
        rho = HLUT[:, 1]
        assert (np.diff(HU) > 0).all(), "HU table is not monotonic in HU"
        assert (
            rho >= 0
        ).all(), "all densities in HU lookup table should be non-negative"
        m = act < HU[0]
        amass[m] = rho[0]
        done |= m
        m = act >= HU[-1]
        amass[m] = rho[-1]
        done |= m
        for hu0, hu1, rho0, rho1 in zip(HU[:-1], HU[1:], rho[:-1], rho[1:]):
            m = (act >= hu0) * (act < hu1)
            assert not (m * done).any(), "programming error"
            amass[m] = rho0
            amass[m] += (act[m] - hu0) * (rho1 - rho0) / (hu1 - hu0)
            done |= m
        assert done.all(), "programming error"
    else:
        n = HLUT.shape[0]
        HUfrom = HLUT[:, 0]
        HUtill = HLUT[:, 1]
        rho = HLUT[:, 2]
        assert (HUfrom < HUtill).all(), "inconsistent HU interval"
        assert (rho > 0).all(), "rho should be positive"
        if n > 1:
            assert (
                HUfrom[1:] == HUtill[:-1]
            ).all(), "HU intervals should be contiguous"
        m = act >= HUfrom[0]
        assert (
            m.all()
        ), "Some HU values in the CT are less than the minimum in the HU table."
        for hu0, hu1, rho0 in zip(HUfrom, HUtill, rho):
            m = (act >= hu0) * (act < hu1)
            assert not (m * done).any(), "programming error"
            amass[m] = rho0
            done |= m
    for hu, rho in overrides.items():
        assert hu == int(hu), "overrides must be given for integer HU values"
        assert rho >= 0, "override density values must be non-negative"
        m = act == hu
        amass[m] = rho
        done |= m
    # if not done.all():
    #     logger.warn("not all voxels got a mass, some voxels are 0")
    mass = itk.GetImageFromArray(amass)
    mass.CopyInformation(ct)
    return mass


def mhd_2_dicom_dose(
    img_mhd, rtplan, beamnr, filename, *, ds={}, physical=True, phantom=False
):
    """
    Parameters
    ----------
    * rtplan: a pydicom Dataset object containing a PBS ion beam plan.
    * beamnr: a *string* containing the beam number to be used for referral. Should contain "PLAN" for plan dose files.
    * phantom: boolean flag to indicate whether this is for a CT (False) or phantom dose (True).
    * img_mhd : itk image. Image to write in dicom dose file.
    * filename : full path of the dicom file to save.
    * ds : dictionary with extra tags to write (e.g. a reference dicom object). The default is {}.
    * physical : Bool for physical dose. The default is True. If False, dose is effective.

    Returns
    -------
    None.

    """
    # create default dcm template
    dcm_ds = create_dicom_dose_template(rtplan, beamnr, phantom=phantom)

    # get info from image
    img = itk.GetArrayFromImage(img_mhd)
    img_size = img_mhd.GetLargestPossibleRegion().GetSize()
    img_spacing = img_mhd.GetSpacing()
    img_origin = img_mhd.GetOrigin()

    # set image information
    img = np.round(img).astype("uint16")
    dcm_ds.PixelData = img.tobytes()
    dcm_ds.Rows = img_size[1]
    dcm_ds.Columns = img_size[0]
    dcm_ds.NumberOfFrames = img_size[2]
    dcm_ds.PixelSpacing[0] = img_spacing[1]
    dcm_ds.PixelSpacing[1] = img_spacing[0]
    dcm_ds.SliceThickness = img_spacing[2]
    dcm_ds.ImagePositionPatient = list(img_origin)
    dcm_ds.DoseType = "PHYSICAL" if physical else "EFFECTIVE"

    # set additional fields
    for k, v in ds.items():
        print(k)
        dcm_ds[k] = v

    dcm_ds.save_as(filename)
    print("File saved.")


def create_dicom_dose_template(rtplan, beamnr, phantom=False):
    """
    Create a template DICOM file for storing a dose distribution corresponding to a given treatment plan.
    * rtplan: a pydicom Dataset object containing a PBS ion beam plan.
    * beamnr: a *string* containing the beam number to be used for referral. Should contain "PLAN" for plan dose files.
    * phantom: boolean flag to indicate whether this is for a CT (False) or phantom dose (True).
    """
    unique_id = pydicom.uid.generate_uid()  # create a new unique UID
    plandose = beamnr.upper() == "PLAN"

    # File meta info data elements
    file_meta = FileMetaDataset()
    file_meta.FileMetaInformationGroupLength = (
        200  # maybe 210 for phantoms (can also be RS6 vs RS5)
    )
    file_meta.FileMetaInformationVersion = b"\x00\x01"
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.2"
    file_meta.MediaStorageSOPInstanceUID = unique_id
    file_meta.TransferSyntaxUID = "1.2.840.10008.1.2"
    # FIXME: we probably need to apply for an official UID here
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.1.2.100.6.40.0.76"
    if sys.version_info.major == 3:
        file_meta.ImplementationVersionName = "DicomObjects.NET"
    else:
        file_meta.ImplementationVersionName = "DicomObjects.NET"

    # Main data elements
    now = datetime.now()
    ds = FileDataset("", {}, file_meta=file_meta, preamble=b"\0" * 128)

    ds.AccessionNumber = ""
    ds.Manufacturer = (
        "ACMIT Gmbh and EBG MedAustron GmbH and Medical University of Vienna"  ###
    )
    ds.ManufacturerModelName = "IDEAL"  ###
    # ds.SoftwareVersions = ideal_version.tag ###
    ds.PositionReferenceIndicator = ""

    ds.SpecificCharacterSet = "ISO_IR 100"
    ds.InstanceCreationDate = now.strftime("%Y%m%d")  #'20171121' ###
    ds.InstanceCreationTime = now.strftime("%H%M%S")  # '120041' ###
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.481.2"
    ds.SOPInstanceUID = unique_id  # '1.2.752.243.1.1.20180817170901595.1980.23430' ###
    ds.StudyDate = str(rtplan.StudyDate)  # '20171103' ###
    ds.StudyTime = str(rtplan.StudyTime)  # '153709' ###
    ds.Modality = "RTDOSE"
    ds.ReferringPhysicianName = str(rtplan.ReferringPhysicianName)  # 'Anonymized' ###
    if "SeriesDescription" in rtplan:
        ds.SeriesDescription = str(rtplan.SeriesDescription)  ###
    if "OperatorsName" in rtplan:
        ds.OperatorsName = str(rtplan.OperatorsName)  ###
    if "PatientName" in rtplan:
        ds.PatientName = str(rtplan.PatientName)  ###
    if "PatientID" in rtplan:
        ds.PatientID = str(rtplan.PatientID)  ###
    if "PatientBirthDate" in rtplan:
        ds.PatientBirthDate = str(rtplan.PatientBirthDate)  ###
    if "PatientSex" in rtplan:
        ds.PatientSex = str(rtplan.PatientSex)  ###
    ds.SliceThickness = str("1")  ### overwrite by postprocessing
    ds.StudyInstanceUID = rtplan.StudyInstanceUID.strip()  ###
    ds.SeriesInstanceUID = rtplan.SeriesInstanceUID.strip()  ###
    if hasattr(rtplan, "StudyDescription"):
        ### absent for phantom/commissioning
        ds.StudyDescription = str(rtplan.StudyDescription)
    if hasattr(rtplan, "PatientIdentityRemoved"):
        ds.PatientIdentityRemoved = str(
            rtplan.PatientIdentityRemoved
        )  ### absent for phantom/commsissioning plans
        ds.DeidentificationMethod = str(
            rtplan.DeidentificationMethod
        )  ### absent for phantom/commsissioning plans
    if hasattr(rtplan, "StudyID"):
        ds.StudyID = rtplan.StudyID  ###
    if hasattr(rtplan, "SeriesNumber"):
        ds.SeriesNumber = rtplan.SeriesNumber  ###
    if phantom:
        ds.InstanceNumber = 0  # str("0") ### only for phantom/commissioning
        ds.PatientOrientation = str("")  ### only for phantom/commissioning
    ds.ImagePositionPatient = [
        str(-999.999),
        str(-999.999),
        str(-999.999),
    ]  ### overwrite by postprocessing
    ds.ImageOrientationPatient = [str(float(c)) for c in "100010"]
    ds.FrameOfReferenceUID = rtplan.FrameOfReferenceUID.strip()  ###
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.NumberOfFrames = str(9)  ### overwrite by postprocessing
    ds.FrameIncrementPointer = pydicom.tag.BaseTag(
        0x3004000C
    )  # That is the tag corresponding to the "GridFrameOffsetVector". All RS dose files do it like this.
    ds.Rows = 9  ### overwrite by postprocessing
    ds.Columns = 9  ### overwrite by postprocessing
    ds.PixelSpacing = [str("9"), str("9")]  ### overwrite by postprocessing
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.DoseUnits = "GY"
    ds.DoseType = "PHYSICAL"  ### TODO: for RBE we may want "effective"
    ds.DoseSummationType = "PLAN" if plandose else "BEAM"  ### beam/plan difference
    ds.GridFrameOffsetVector = [str(c) for c in range(9)]
    ds.DoseGridScaling = 0.999999  ### overwrite by postprocessing

    # Referenced RT Plan Sequence
    refd_rt_plan_sequence = Sequence()
    ds.ReferencedRTPlanSequence = refd_rt_plan_sequence

    # Referenced RT Plan Sequence: Referenced RT Plan 1
    refd_rt_plan1 = Dataset()
    refd_rt_plan1.ReferencedSOPClassUID = (
        "1.2.840.10008.5.1.4.1.1.481.8"  ### different for phantoms??? check
    )
    refd_rt_plan1.ReferencedSOPInstanceUID = rtplan.SOPInstanceUID.strip()

    if not plandose:
        # Referenced Fraction Group Sequence ## ONLY FOR BEAMS
        refd_frxn_gp_sequence = Sequence()  ## ONLY FOR BEAMS
        refd_rt_plan1.ReferencedFractionGroupSequence = (
            refd_frxn_gp_sequence  ## ONLY FOR BEAMS
        )

        # Referenced Fraction Group Sequence: Referenced Fraction Group 1 ## ONLY FOR BEAMS
        refd_frxn_gp1 = Dataset()  ## ONLY FOR BEAMS

        # Referenced Beam Sequence ## ONLY FOR BEAMS
        refd_beam_sequence = Sequence()  ## ONLY FOR BEAMS
        refd_frxn_gp1.ReferencedBeamSequence = refd_beam_sequence  ## ONLY FOR BEAMS

        # Referenced Beam Sequence: Referenced Beam 1 ## ONLY FOR BEAMS
        refd_beam1 = Dataset()  ## ONLY FOR BEAMS
        refd_beam1.ReferencedBeamNumber = beamnr  ### ## ONLY FOR BEAMS
        refd_beam_sequence.append(refd_beam1)  ## ONLY FOR BEAMS

        refd_frac_grp_nr = None
        for f in rtplan.FractionGroupSequence:
            fnr = str(f.FractionGroupNumber)
            if refd_frac_grp_nr is None:
                # In case the beam number is not actually found, this is a bit of a lie.
                # But we have to survive somehow when the user feeds us illegal DICOM plan files from PDM.
                refd_frac_grp_nr = fnr
            for refb in f.ReferencedBeamSequence:
                if str(refb.ReferencedBeamNumber) == str(beamnr):
                    refd_frac_grp_nr = fnr
                    break
        refd_frxn_gp1.ReferencedFractionGroupNumber = (
            refd_frac_grp_nr  ## ONLY FOR BEAMS
        )
        refd_frxn_gp_sequence.append(refd_frxn_gp1)  ## ONLY FOR BEAMS
    refd_rt_plan_sequence.append(refd_rt_plan1)

    ds.PixelData = np.ones(
        (9, 9, 9), dtype=np.uint16
    ).tobytes()  ### overwrite by postprocessing

    ds.file_meta = file_meta
    ds.is_implicit_VR = True
    ds.is_little_endian = True
    # ds.save_as(filename, write_like_original=False) ###

    return ds


if __name__ == "__main__":
    mhd_path = "/home/fava/opengate/opengate/tests/output/output_test051_rtp/threeDdoseWater.mhd"
    img_mhd = itk.imread(mhd_path)
    mhd_2_dicom_dose(
        img_mhd,
        "/home/fava/opengate/opengate/tests/output/output_test051_rtp/my_dicom.dcm",
    )
