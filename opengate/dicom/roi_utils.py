# -----------------------------------------------------------------------------
#   Copyright (C): MedAustron GmbH, ACMIT Gmbh and Medical University Vienna
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE for further details
# -----------------------------------------------------------------------------

"""
This module was developed in as part of the effort in Uppsala (2015-2017)
develop a framework to analyze the effect of patient motion on the dose
distribution in proton PBS (primarily at Skandion, but it should work for
other clinics as well).
Authors: David Boersma and Pierre Granger
"""

from .helpers_dcm import bounding_box
import itk
import numpy as np
import matplotlib.path  # for useful Path class, not for plotting...

# tolerances for dose histograms
negative_tol = 1e-4
nb_negative_tol = 5


def list_roinames(ds):
    """
    Return the names of the ROIs in a given dicom structure set as a list of strings.
    """
    assert hasattr(ds, "StructureSetROISequence")
    assert hasattr(ds, "ROIContourSequence")
    # these sequences are actually not always equally long
    # as long as the 'referenced ROI number' of the contours are in the roi sequence, we can pray that everything is fine
    # assert(len(ds.ROIContourSequence)==len(ds.StructureSetROISequence))
    return [str(ssroi.ROIName) for ssroi in ds.StructureSetROISequence]


def list_roinumbers(ds):
    """
    Return the names of the ROIs in a given dicom structure set as a list of strings.
    """
    assert hasattr(ds, "StructureSetROISequence")
    assert hasattr(ds, "ROIContourSequence")
    # these sequences are actually not always equally long
    # as long as the 'referenced ROI number' of the contours are in the roi sequence, we can pray that everything is fine
    # assert(len(ds.ROIContourSequence)==len(ds.StructureSetROISequence))
    return [int(ssroi.ROINumber) for ssroi in ds.StructureSetROISequence]


def scrutinize_contour(points):
    """
    Test that `points` is a (n,3) array suitable for contour definition.
    """
    assert hasattr(points, "shape")  # is it an array?
    assert len(points.shape) == 2  # a 2-dim array, I mean?
    assert points.shape[0] >= 3  # we need at least 3 points for a contour
    assert points.shape[1] == 3  # we deal with points in 3-d space ...
    assert (
        len(set(points[:, 2])) == 1
    )  # ... but we assume they all have the same z-coordinate
    # maybe add some more tests


def sum_of_angles(points, name="unspecified", rounded=True, scrutinize=False):
    """
    Code to determine left/right handedness of contour.  We do this by
    computing the angles between each successive segment in the contour. By
    "segment" we mean the difference vector between successive contour points.
    The cross and dot products between two segments are proportional to sine
    and cosine of the angle between the segments, respectively.
    """
    phi = 0.0
    # first: check assumptions
    if scrutinize:
        scrutinize_contour(points)
    # we have more assumptions, but will check them later
    npoints = points.shape[0]
    # for computation convenience we add the first segment
    # (first two points) to the end of the list of points
    pppoints = np.append(points[:, :2], points[:2, :2], axis=0)
    # compute difference vectors (segments)
    dpppoints = np.diff(pppoints, axis=0)
    assert dpppoints.shape == (npoints + 1, 2)
    # array with all unique seqments
    dp0 = dpppoints[:-1]
    # array with all unique seqments, first segment moved to the end
    dp1 = dpppoints[1:]
    assert dp0.shape == (npoints, 2)
    # check that segments have nonzero length
    nonzerodp0 = 0 < np.sum(dp0**2, axis=1)
    if not nonzerodp0.all():
        Ngood = np.sum(nonzerodp0)
        if Ngood < 3:
            # logger.warn("got a pathological contour: only {} out of {} have nonzero line segments".format(Ngood,npoints))
            return np.nan
        else:
            # logger.warn("BUGGY CONTOUR: only {} out of {} have nonzero line segments, going to re-call this function with cleaned point set".format(Ngood,npoints))
            # by applying the nonzero mask on the points vector,
            # we leave out the points that are identical to their next neighbor
            # TODO: check against too deep recursion level (not a big concern here)
            return sum_of_angles(
                points[nonzerodp0], name=name, rounded=rounded, scrutinize=True
            )
    # if the previous works as intended, then the following assert should always pass
    assert nonzerodp0.all()
    # now do ordinary vector calculus: cross product, dot product and norms
    kross = dp0[:, 0] * dp1[:, 1] - dp0[:, 1] * dp1[:, 0]
    dots = dp0[:, 0] * dp1[:, 0] + dp0[:, 1] * dp1[:, 1]
    norms = np.sqrt(np.sum(dp0**2, axis=1) * np.sum(dp1**2, axis=1))
    # this assert is maybe paranoid and superfluous
    assert (norms > 0).all()
    sinphi = kross / norms
    # guard against anomalies due to rounding errors
    sinphi[sinphi > 1] = 1
    sinphi[sinphi < -1] = -1
    # which Quadrant are we in?
    # Q1: less or equal pi/2 to the left
    # Q2: more than pi/2 to the left
    # Q3: more than pi/2 to the right
    # Q4: less or equal pi/2 to the right
    maskQ23 = dots < 0
    maskQ2 = maskQ23 * (sinphi > 0)
    maskQ3 = maskQ23 * (sinphi < 0)
    maskBAD = maskQ23 * (sinphi == 0)
    phi = np.arcsin(sinphi)
    # arcsin returns phi in range -pi .. +pi
    # Q2 (phi>0): phi -> +pi - phi
    # Q3 (phi<0): phi -> -pi - phi
    phi[maskQ23] *= -1
    phi[maskQ2] += np.pi
    phi[maskQ3] -= np.pi
    if maskBAD.any():
        # logger.warn("{} contains {} points where the contour retreats 180 degrees on itself".format(name,np.sum(maskBAD)))
        # logger.warn("this is fixable (remove one or two points) but I did not implement that fix yet.")
        # TODO: is a warning and returning NAN sufficient? Shouldn't we crash and burn here?
        return np.nan
    sum_phi_deg = np.sum(phi) * 180 / np.pi
    round_sum_phi_deg = int(np.round(sum_phi_deg))
    if round_sum_phi_deg == 360:
        pass
        # logger.debug("({}) POSITIVE: inclusion contour".format(name))
    elif round_sum_phi_deg == -360:
        pass
        # logger.debug("({}) NEGATIVE: exclusion contour".format(name))
    else:
        pass
        # logger.warn("({}) weird sum of contour angles: {} degrees, should be + or - 360 degrees".format(name,sum_phi_deg))
    if rounded:
        return round_sum_phi_deg
    else:
        return sum_phi_deg


# "Borrowed" from http://stackoverflow.com/questions/22678990/how-can-i-calculate-the-area-within-a-contour-in-python-using-the-matplotlib
# Use Green's theorem to compute the area
# enclosed by the given contour.
def enclosed_area(vs):
    # logger.debug("vs has shape {}".format(vs.shape))
    a = 0
    x0, y0 = vs[0]
    # logger.debug("x0={} y0={}".format(x0,y0))
    for [x1, y1] in vs[1:]:
        dx = x1 - x0
        dy = y1 - y0
        a += 0.5 * (y0 * dx - x0 * dy)
        # logger.debug("x0={} y0={} x1={} y1={} a={}".format(x0,y0,x1,y1,a))
        x0 = x1
        y0 = y1
    return -a


def test_enclosed_area():
    vs = np.zeros((4, 2), dtype=float)
    vs[1, 0] = 1
    vs[2, 0] = 1
    vs[2, 1] = 1
    vs[3, 1] = 1
    print("unit square: area={}".format(enclosed_area(vs)))
    avs = vs[::-1, :]
    print("reverse unit square: area={}".format(enclosed_area(avs)))


class contour_layer(object):
    """
    This is an auxiliary class for the `region_of_interest` class defined below.
    A `contour_layer` object describes the ROI at one particular z-value.
    It is basically a list of 2D contours. The ones with positive orientation
    (sum of angles between successive contour segments is +360 degrees) will be
    used to for inclusion, the ones with negative orientation (sum of angles is
    -360 degrees) will be used for exclusion. All points of an exclusion
    contour should be included by an inclusion contour.
    """

    def __init__(
        self, points=None, ref=None, name="notset", z=None, ignore_orientation=True
    ):
        self.name = name
        self.inc_always = ignore_orientation
        self.ref = ref
        self.inclusion = []
        self.exclusion = []
        if points is None:
            self.z = z
        else:
            self.z = z if not z is None else points[0, 2]
            self.add_contour(points, ref)

    def __repr__(self):
        return "contour layer {} with {} inclusion(s) and {} exclusion(s) at z = {}".format(
            self.name, len(self.inclusion), len(self.exclusion), self.z
        )

    def add_contour(self, points, ref=None):
        assert len(points) > 2
        assert self.z == points[0, 2]
        if self.ref is None:
            self.ref = ref
        elif not ref is None:
            assert ref == self.ref
        orientation = (
            360.0 if self.inc_always else sum_of_angles(points, name=self.name)
        )
        path = matplotlib.path.Path(points[:, :2])
        if np.around(orientation) == 360:
            self.inclusion.append(path)
        elif np.around(orientation) == -360:
            self.exclusion.append(path)
        else:
            pass
            # logger.error("({}) got a very weird contour a sum of angles equal to {}; z={} ref={}".format(self.name,orientation,len(points),self.z))
        n_inc_points = sum([len(pts) for pts in self.inclusion])
        n_exc_points = sum([len(pts) for pts in self.exclusion])
        # logger.debug("layer {} has {} inclusion path(s) ({} points) and {} exclusion path(s) ({} points)".format(self.ref,len(self.inclusion),n_inc_points,len(self.exclusion),n_exc_points))

    def contains_point(self, point):
        assert len(point) == 2
        is_contained = False
        for q in self.inclusion:
            if q.contains_point(point):
                is_contained = True
                break
        for p in self.exclusion:
            if p.contains_point(point):
                is_contained = False
                break
        return is_contained

    def contains_points(self, xycoords):
        Ncoords = len(xycoords)
        assert xycoords.shape == (Ncoords, 2)
        flatmask = np.zeros(len(xycoords), dtype=bool)
        for q in self.inclusion:
            flatmask |= q.contains_points(xycoords)
        for p in self.exclusion:
            flatmask &= np.logical_not(p.contains_points(xycoords))
        return flatmask

    def correct_mask(self, xymesh, mask, spacing):
        xx, yy = xymesh
        mask = np.reshape(mask, xx.shape)
        mask = mask.astype(float)
        ref_area = spacing[0] * spacing[1]
        sparseintsc = dict()
        for q in self.inclusion:
            for k in range(len(q.vertices)):
                seg = (q.vertices[k], q.vertices[k - 1])
                xmin = min(seg[0][0], seg[1][0])
                xmax = max(seg[0][0], seg[1][0])
                ymin = min(seg[0][1], seg[1][1])
                ymax = max(seg[0][1], seg[1][1])
                jmin = max(xx[0, :].searchsorted(xmin) - 2, 0)
                jmax = xx[0, :].searchsorted(xmax + 2)
                imin = max(yy[:, 0].T.searchsorted(ymin) - 2, 0)
                imax = yy[:, 0].T.searchsorted(ymax + 2)
                for i in range(imin, imax):
                    for j in range(jmin, jmax):
                        bl = (xx[i, j] - 0.5 * spacing[0], yy[i, j] - 0.5 * spacing[1])
                        br = (xx[i, j] + 0.5 * spacing[0], yy[i, j] - 0.5 * spacing[1])
                        tl = (xx[i, j] - 0.5 * spacing[0], yy[i, j] + 0.5 * spacing[1])
                        tr = (xx[i, j] + 0.5 * spacing[0], yy[i, j] + 0.5 * spacing[1])
                        intersect_list = list()
                        segments = [(bl, br), (br, tr), (tr, tl), (tl, bl)]

                        for n, seg2 in enumerate(segments):
                            intsc = intersect_segments(np.array(seg2), np.array(seg))
                            if intsc.any():
                                intersect_list.append([intsc, n])
                                if len(intersect_list) == 2:
                                    break
                        if intersect_list:
                            if sparseintsc.get((i, j)):
                                sparseintsc[(i, j)] = (
                                    sparseintsc[(i, j)] + intersect_list
                                )
                            else:
                                sparseintsc[(i, j)] = intersect_list

        for (i, j), intersect_list in sparseintsc.items():
            if len(intersect_list) == 2:
                bl = (xx[i, j] - 0.5 * spacing[0], yy[i, j] - 0.5 * spacing[1])
                br = (xx[i, j] + 0.5 * spacing[0], yy[i, j] - 0.5 * spacing[1])
                tl = (xx[i, j] - 0.5 * spacing[0], yy[i, j] + 0.5 * spacing[1])
                tr = (xx[i, j] + 0.5 * spacing[0], yy[i, j] + 0.5 * spacing[1])
                segments = [(bl, br), (br, tr), (tr, tl), (tl, bl)]

                if abs(intersect_list[0][1] - intersect_list[1][1]) == 2:
                    if intersect_list[0][1] % 2 == 1:
                        area = (
                            0.5
                            * min(
                                abs(
                                    intersect_list[0][0][1]
                                    - 2 * bl[1]
                                    + intersect_list[1][0][1]
                                ),
                                abs(
                                    intersect_list[0][0][1]
                                    - 2 * tl[1]
                                    + intersect_list[1][0][1]
                                ),
                            )
                            * spacing[0]
                        )
                        mask[i, j] = (
                            (1 - area / ref_area)
                            if (mask[i, j] == 1.0)
                            else (area / ref_area)
                        )
                    else:
                        area = (
                            0.5
                            * min(
                                abs(
                                    intersect_list[0][0][0]
                                    - 2 * bl[0]
                                    + intersect_list[1][0][0]
                                ),
                                abs(
                                    intersect_list[0][0][0]
                                    - 2 * br[0]
                                    + intersect_list[1][0][0]
                                ),
                            )
                            * spacing[1]
                        )
                        mask[i, j] = (
                            (1 - area / ref_area)
                            if (mask[i, j] == 1.0)
                            else (area / ref_area)
                        )
                else:
                    intersect_list = sorted(intersect_list, key=lambda elt: elt[1])
                    corner = segments[intersect_list[0][1]][1]
                    area = (
                        0.5
                        * max(
                            abs(corner[0] - intersect_list[0][0][0]),
                            abs(corner[0] - intersect_list[1][0][0]),
                        )
                        * max(
                            abs(corner[1] - intersect_list[0][0][1]),
                            abs(corner[1] - intersect_list[1][0][1]),
                        )
                    )
                    mask[i, j] = (
                        (1 - area / ref_area)
                        if (mask[i, j] == 1.0)
                        else (area / ref_area)
                    )
        return mask.flat

    def check(self):
        assert len(self.inclusion) > 0  # really?
        for p in self.exclusion:
            ok = False
            for q in self.inclusion:
                if q.contains_path(p):
                    ok = True
                    # logger.debug("({}) layer {} exclusion contour check OK".format(self.name,self.z))
                break
            if not ok:
                # logger.critical("({}) exclusion contour at z={} not contained in any inclusion contour".format(self.name,self.z))
                raise RuntimeError("contour error")
        # logger.debug("({}) layer {} check OK".format(self.name,self.z))

    def get_area(self):
        a = 0.0
        for q in self.inclusion:
            qa = enclosed_area(q.vertices)
            assert qa >= 0
            # logger.debug("{} z={}: adding {} mm2 from inclusion".format(self.name,self.z,qa))
            a += qa
        for p in self.exclusion:
            pa = enclosed_area(p.vertices)
            # logger.debug("{} z={}: subtracting {} mm2 from exclusion".format(self.name,self.z,-pa))
            assert pa <= 0
            a += pa
        return a


def check_roi(ds, roi_id):
    # Beware: the three sequences for structureset (name,nr), observation (type), contoursets (actual contours) are NOT necessarily synchronous.
    # So you can NOT zip these sequences. The exceptions would bite you badly.
    for ssroi in ds.StructureSetROISequence:
        if (str(roi_id) == str(ssroi.ROINumber)) or (str(roi_id) == str(ssroi.ROIName)):
            roinumber = str(ssroi.ROINumber)
            roiname = str(ssroi.ROIName)
            for roi in ds.ROIContourSequence:
                if str(roi.ReferencedROINumber) == roinumber:
                    # logger.debug("found ROI contour; nr={} and name={}".format(roinumber,roiname))
                    return (roi, roinumber, roiname)
        else:  # debug
            pass
            # logger.debug("{} != {} and != {}".format(roi_id,ssroi.ROINumber,ssroi.ROIName))
    # logger.error("ROI with id {} not found; structure set contains: ".format(roi_id) + ", ".join(list_roinames(ds)))
    raise ValueError("ROI with id {} not found".format(roi_id))


class region_of_interest(object):
    def __init__(self, ds=None, roi_id=None, verbose=False, contours_list=None):
        if contours_list is not None:
            self.from_contours(contours_list)
            return
        # assert(len(ds.ROIContourSequence)==len(ds.StructureSetROISequence))
        roi, self.roinr, self.roiname = check_roi(ds, roi_id)
        self.ncontours = len(roi.ContourSequence)
        self.npoints_total = sum([len(c.ContourData) for c in roi.ContourSequence])
        self.bb = bounding_box()
        # we are sort the contours by depth-coordinate
        self.contour_layers = []
        self.zlist = []
        self.dz = 0.0
        self.maskparameters = []
        self.masklist = []
        # self.contour_refs=[]
        for contour in roi.ContourSequence:
            ref = contour.ContourImageSequence[0].ReferencedSOPInstanceUID
            npoints = int(contour.NumberOfContourPoints)
            # check assumption on number of contour coordinates
            assert len(contour.ContourData) == 3 * npoints
            points = np.array([float(coord) for coord in contour.ContourData]).reshape(
                npoints, 3
            )
            zvalues = set(points[:, 2])
            # check assumption that all points are in the same xy plane (constant z)
            assert len(zvalues) == 1
            zvalue = zvalues.pop()
            if zvalue in self.zlist:
                ic = self.zlist.index(zvalue)
                self.contour_layers[ic].add_contour(points, ref)
            else:
                self.contour_layers.append(contour_layer(points, ref))
                self.zlist.append(zvalue)
            self.bb.should_contain_all(points)
        if verbose:
            pass
            # logger.info("roi {}={} has {} points on {} contours with z range [{},{}]".format(
            # self.roinr,self.roiname,self.npoints_total,self.ncontours,self.bb.zmin,self.bb.zmax))
        for layer in self.contour_layers:
            layer.check()
        dz = set(np.diff(self.zlist))
        if len(dz) == 1:
            self.dz = dz.pop()
        else:
            dz = set(np.diff(np.around(self.zlist, decimals=6)))
            if len(dz) == 1:
                self.dz = dz.pop()
            else:
                # logger.warn("{} not one single z step: {}".format(self.roiname,", ".join([str(d) for d in dz])))
                self.dz = 0.0

    def get_mask_from_parameters(self, img_params):
        if img_params in self.maskparameters:
            return self.masklist[self.maskparameters.index(img_params)]
        else:
            return None

    def from_contours(self, contours_list):
        self.roiname = "Arficial roi created from scratch"
        self.roinr = 1337
        self.ncontours = len(contours_list)
        self.npoints_total = 0
        self.bb = bounding_box()
        self.contour_layers = []
        self.zlist = []
        self.dz = 0.0
        self.maskparameters = []
        self.masklist = []
        for contour_layer in contours_list:
            z = contour_layer.z
            self.zlist.append(z)
            self.contour_layers.append(contour_layer)
        zlist = sorted(self.zlist)
        dz = set(np.diff(zlist))
        if len(dz) == 1:
            self.dz = dz.pop()
        else:
            dz = set(np.diff(np.around(zlist, decimals=6)))
            if len(dz) == 1:
                self.dz = dz.pop()
            else:
                # logger.warn("{} not one single z step: {}".format(self.roiname,", ".join([str(d) for d in dz])))
                self.dz = 0.0
        points = np.empty((0, 3))
        for layer in contours_list:
            for contour in layer.inclusion:
                z_col = np.empty((contour.vertices.shape[0], 1))
                z_col.fill(layer.z)
                points = np.vstack((points, np.hstack((contour.vertices, z_col))))
        self.bb.should_contain_all(points)
        self.npoints_total = points.shape[0]

    def __repr__(self):
        return "roi {} defined by contours in {} layers, {}".format(
            self.roiname, len(self.contour_layers), self.bb
        )

    def have_mask(self):
        return self.dz != 0.0

    def get_volume(self):
        vol = 0.0
        for i, layer in enumerate(self.contour_layers, 1):
            area = layer.get_area()
            cvol = self.dz * area
            vol += cvol
            # logger.debug("{}. got volume = dz * area = {} * {} = {}, sum={}".format(i,self.dz,area,cvol,vol))
        return vol

    def get_mask(self, img, zrange=None, corrected=True):
        """
        For a given image, compute for every voxel whether it is inside the ROI or not.
        The `zrange` can be used to limit the z-range of the ROI.
        If specified, the `zrange` should be contained in the z-range of the given image.
        """
        if not self.have_mask():
            # logger.warn("Irregular z-values, masking not yet supported")
            return None
        dims = np.array(img.GetLargestPossibleRegion().GetSize())
        if len(dims) != 3:
            # logger.error("ERROR only 3d images supported")
            return None
        ##logger.debug("create roi mask image object with dims={}".format(dims))
        if corrected:
            # logger.debug("{} going to get mask with 'corrected' float weights".format(self.roiname))
            aroimask = np.zeros(dims[::-1], dtype=np.float32)
        else:
            # logger.debug("{} going to get mask with 'uncorrected' binary weights".format(self.roiname))
            aroimask = np.zeros(dims[::-1], dtype=np.uint8)
        roimask = itk.GetImageFromArray(aroimask)
        roimask.CopyInformation(img)
        orig = roimask.GetOrigin()
        space = roimask.GetSpacing()
        roisize = np.array(roimask.GetLargestPossibleRegion().GetSize())
        if (roisize != dims).any():
            # logger.error("roimask size {} differs from img size {}".format(roisize,dims))
            raise RuntimeError("array size error!")
        #############################################################################################
        # check that the bounding box of this ROI is contained within the volume of the given image #
        #############################################################################################
        contained = True
        for o, s, d, rmin, rmax in zip(
            orig, space, dims, self.bb.mincorner, self.bb.maxcorner
        ):
            contained &= int(np.round(rmin - o) / s) in range(d)
            contained &= int(np.round(rmax - o) / s) in range(d)
        if not contained:
            pass
            # logger.warn('DUIZEND BOMMEN EN GRANATEN orig={} space={} dims={} bbroi={}'.format(orig,space,dims,self.bb))
        else:
            pass
            # logger.debug('YAY: roi "{}" is contained in image'.format(self.roiname))
        ##logger.debug("copied infor orig={} spacing={}".format(orig,space))
        # ITK: the "origin" has the coordinates of the *center* of the corner voxel
        # zmin and zmax are the z coordinates of the boundary of the volume
        zmin = orig[2] - 0.5 * space[2]
        zmax = orig[2] + (dims[2] - 0.5) * space[2]
        eps = 0.001 * np.abs(self.dz)
        ##logger.debug("got point mesh")
        if zmin - eps > self.bb.zmax + self.dz or zmax + eps < self.bb.zmin - self.dz:
            # logger.warn("WARNING: no overlap in z ranges")
            # logger.warn("WARNING: img z range [{}-{}], roi z range [{}-{}]".format(zmin,zmax,self.zmin,self.zmax))
            return roimask
        img_params = [orig, space, dims, zrange]
        if zrange is None:
            zrange = (zmin, zmax)
        else:
            assert len(zrange) == 2
            assert zrange[0] >= zmin
            assert zrange[1] <= zmax
            if (
                zrange[0] - eps > self.bb.zmax + self.dz
                or zrange[1] + eps < self.bb.zmin - self.dz
            ):
                # logger.warn("WARNING: no overlap in (restricted) z ranges")
                return roimask
        # #logger.debug("zmin={} zmax={}".format(zmin,zmax))
        # xpoints and ypoints contain the x/y coordinates of the voxel centers
        xpoints = np.linspace(orig[0], orig[0] + space[0] * dims[0], dims[0], False)
        ypoints = np.linspace(orig[1], orig[1] + space[1] * dims[1], dims[1], False)
        xymesh = np.meshgrid(xpoints, ypoints)
        xyflat = np.array([(x, y) for x, y in zip(xymesh[0].flat, xymesh[1].flat)])
        clayer0 = self.contour_layers[0]
        ##logger.debug contour0pts.shape
        z0 = clayer0.z
        ##logger.debug("z0={}".format(z0))
        ##logger.debug("going to loop over z planes in image")
        for iz in range(dims[2]):
            z = orig[2] + space[2] * iz  # z coordinate in image/mask
            if z < zrange[0] or z > zrange[1]:
                continue
            icz = int(np.round((z - z0) / self.dz))  # layer index
            if icz >= 0 and icz < len(self.contour_layers):
                # logger.debug("INSIDE roi: z index mask/image iz={} (z={}) layer index icz={} (z={})".format(iz,z,icz,self.contour_layers[icz].z))
                flatmask = self.contour_layers[icz].contains_points(xyflat)
                # logger.debug("got {} points inside".format(np.sum(flatmask)))
                if corrected:
                    flatmask = flatmask.astype(float)
                    flatmask = self.contour_layers[icz].correct_mask(
                        xymesh, flatmask, space
                    )
                    for iflat, b in enumerate(flatmask):
                        if not b:
                            continue
                        ix = iflat % dims[0]
                        iy = iflat // dims[0]
                        # x = orig[0]+space[0]*ix # x coordinate in image/mask
                        # y = orig[1]+space[1]*iy # y coordinate in image/mask
                        # assert(self.contour_layers[icz].contains_point(point=(x,y)))
                        try:
                            roimask[ix, iy, iz] = b
                        except IndexError as inderr:
                            # logger.error("iflat={} ix={} iy={} iz={}, error={}".format(iflat,ix,iy,iz,inderr))
                            raise
                else:
                    flatmask = flatmask.astype(int)
                    aroimask[iz, :, :] = flatmask.reshape(dims[1], dims[0])[:, :]
            elif icz < 0:
                pass
                # logger.debug("BELOWroi: z index mask/image iz={} (z={}) layer index icz={} (z0={} dz={})".format(iz,z,icz,z0,self.dz))
            else:
                pass
                # logger.debug("ABOVE roi: z index mask/image iz={} (z={}) layer index icz={} (z0={} dz={} nlayer={})".format(iz,z,icz,z0,self.dz,len(self.contour_layers)))
        # logger.debug("got mask with {} enabled voxels out of {}".format(np.sum(aroimask>0),np.prod(aroimask.shape)))
        if not corrected:
            roimask = itk.GetImageFromArray(aroimask)
            roimask.CopyInformation(img)
            # achk = sitk.GetArrayFromImage(roimask)
            # ndiff = np.sum(achk!=aroimask)
            # nsame = np.sum(achk==aroimask)
            # nboth = np.sum((achk>0)*(aroimask>0))
            # nachk = np.sum(achk>0)
            # naroi = np.sum(aroimask>0)
            ##logger.debug("N(chk)={} N(aroi)={} ndiff={} nsame={} nboth={}".format(nachk,naroi,ndiff,nsame,nboth))
        self.maskparameters.append(img_params)
        self.masklist.append(roimask)
        # logger.debug("returning mask")
        return roimask

    def get_dvh(
        self, img, nbins=100, dmin=None, dmax=None, zrange=None, debuglabel=None
    ):
        # logger.debug("starting dvh calculation")
        dims = np.array(img.GetLargestPossibleRegion().GetSize())
        if len(dims) != 3:
            # logger.error("ERROR only 3d images supported")
            return None
        # logger.debug("got size = {}".format(dims.tolist()))
        aimg = itk.GetArrayFromImage(img)
        # logger.debug("got array with shape {}".format(list(aimg.shape)))
        img_params = [
            img.GetOrigin(),
            img.GetSpacing(),
            np.array(img.GetLargestPossibleRegion().GetSize()),
            zrange,
        ]
        itkmask = self.get_mask_from_parameters(img_params)
        if itkmask:
            pass
            # logger.debug("Using already computed mask for these dimensions")
        else:
            itkmask = self.get_mask(img, zrange)
        # logger.debug("got mask with size {}".format(itkmask.GetLargestPossibleRegion().GetSize()))
        amask = itk.GetArrayFromImage(itkmask)

        if dmin is None:
            dmin = np.min(aimg)
        if dmax is None:
            dmax = np.max(aimg)
        # logger.debug("Specified dmin={} dmax={}".format(dmin,dmax))
        a = aimg[np.nonzero(amask)]
        # logger.debug("Dose dmin={} dmax={}".format(np.min(a),np.max(a)))
        nb_negative = np.sum(a < 0)
        assert nb_negative <= nb_negative_tol
        assert not np.any(a < -negative_tol)
        a[a < 0] = 0
        if nb_negative:
            # logger.warning("There are {} negative voxels in the mask !! OK because below {}".format(nb_negative, nb_negative_tol))
            pass
        dhist, dedges = np.histogram(
            a, bins=nbins, range=(dmin, dmax), weights=amask[np.nonzero(amask)]
        )
        # logger.debug("got histogram with {} edges for {} bins".format(len(dedges),nbins))
        adhist = np.array(dhist, dtype=float)
        adedges = np.array(dedges, dtype=float)
        dsum = 0.5 * np.sum(adhist * adedges[:-1] + adhist * adedges[1:])
        dhistsum = np.sum(adhist)
        amasksum = np.sum(amask)
        adchist = np.cumsum(adhist)
        # logger.debug("dhistsum={} amasksum={} adchist[-1]={}".format(dhistsum,amasksum,adchist[-1]))
        assert round(amasksum, 7) == round(dhistsum, 7)
        assert round(amasksum, 7) == round(adchist[-1], 7)
        # logger.debug("survived assert")
        d02 = None
        d50 = None
        d98 = None
        if dhistsum > 0:
            # logger.debug("getting d50 and d98")
            dsum98 = 0.98 * dhistsum
            dsum50 = 0.50 * dhistsum
            dsum02 = 0.02 * dhistsum
            i98 = adchist.searchsorted(dsum98)
            i50 = adchist.searchsorted(dsum50)
            i02 = adchist.searchsorted(dsum02)
            assert i98 > 0
            assert i50 > 0
            assert i02 > 0
            dd98 = adchist[i98] - adchist[i98 - 1]
            dd50 = adchist[i50] - adchist[i50 - 1]
            dd02 = adchist[i02] - adchist[i02 - 1]
            # dd50 = adhist[i50]
            # dd02 = adhist[i02]
            assert dd98 > 0
            assert dd50 > 0
            assert dd02 > 0
            # interpolate
            d98 = (
                (adchist[i98] - dsum98) * dedges[i98 - 1]
                + (dsum98 - adchist[i98 - 1]) * dedges[i98]
            ) / dd98
            d50 = (
                (adchist[i50] - dsum50) * dedges[i50 - 1]
                + (dsum50 - adchist[i50 - 1]) * dedges[i50]
            ) / dd50
            d02 = (
                (adchist[i02] - dsum02) * dedges[i02 - 1]
                + (dsum02 - adchist[i02 - 1]) * dedges[i02]
            ) / dd02
            # convert from normal statistics to medical physics statistics conventions
            # logger.debug("getting dvh")
            dvh = -1.0 * adchist / dhistsum + 1.0
            d02, d98 = d98, d02
            # logger.info("D02={} D50={} D98={}".format(d02,d50,d98))
            # logger.debug("got dvh with dsum={} dvh[0]={} adchist[0]={}".format(dsum,dvh[0],adchist[0]))
        else:
            pass
            # logger.warn("dhistsum is zero or negative")
        return dvh, dedges, dhistsum, dsum, d02, d50, d98

    # def intersect_with(self, rois_list):
    #    contour_layers_intsc = list()
    #    if(not rois_list):
    #        return self
    #    for roi in rois_list:
    #        for lay1 in roi.contour_layers:
    #            for lay2 in self.contour_layers:
    #                if(lay2.z == lay1.z):
    #                    intersect_layer = contour_layer(z=lay1.z)
    #                    for q1 in lay1.inclusion:
    #                        for q2 in lay2.inclusion:
    #                            poly1 = Polygon(q1.vertices)
    #                            poly2 = Polygon(q2.vertices)
    #                            intsc = poly1.intersection(poly2)
    #                            cont = matplotlib.path.Path(intsc.exterior.coords) if intsc else False
    #                            if(cont):
    #                                intersect_layer.inclusion.append(cont)
    #                    contour_layers_intsc.append(intersect_layer)
    #    roi_intsc = region_of_interest(contours_list=contour_layers_intsc)
    #    return roi_intsc


def get_intersection_volume(roilist, xvoxel=1.0, yvoxel=1.0):
    # There is probably a clever way to compute this by constructing
    # an "intersection contour" for each layer: for each contour, keep only
    # points that are inside all other contours in the list. But is tough to then
    # put those points in the right order.
    # Instead we'll just make a grid of points and get the volume of the combined mask.
    # With xvoxel and yvoxel the caller can tweak the voxel size of the mask in x and y.
    # In z the voxel size is given by the incoming ROIs.
    dz = min([r.dz for r in roilist])
    assert dz > 0
    assert xvoxel > 0
    assert yvoxel > 0
    bb = bounding_box(bb=roilist[0].bb)
    for roi in roilist[1:]:
        bb.intersect(roi.bb)
    if bb.empty:
        # too bad
        return 0.0
    spacing = np.array([xvoxel, yvoxel, dz], dtype=float)
    bb.add_margins(2 * spacing)
    dimsize = np.array(np.round((bb.maxcorner - bb.mincorner) / spacing), dtype=int)
    # img = sitk.Image(dimsize,sitk.sitkUInt8)
    img = itk.GetImageFromArray(np.zeros(dimsize[::-2], dtype=np.uint8))
    img.SetOrigin(bb.mincorner)
    img.SetSpacing(spacing)
    itkmask = itk.GetArrayFromImage(roilist[0].get_mask(img))
    for roi in roilist[1:]:
        itkmask *= itk.GetArrayFromImage(roi.get_mask(img))
    return np.sum(itkmask) * np.prod(spacing)


def intersect_segments(S1, S2, eps=1e-10):
    perp = lambda u, v: (u[0] * v[1] - v[0] * u[1])
    u = S1[1] - S1[0]
    v = S2[1] - S2[0]
    w = S1[0] - S2[0]
    D = perp(u, v)

    if abs(D) < eps:
        # if(not np.any(u-v)):
        #     return S1[1]
        return np.array([])
    sI = (v[0] * w[1] - v[1] * w[0]) / D
    if sI < 0 or sI > 1:
        return np.array([])
    tI = (u[0] * w[1] - u[1] * w[0]) / D
    if tI < 0 or tI > 1:
        return np.array([])
    return S1[0] + sI * u


# vim: set et softtabstop=4 sw=4 smartindent:
