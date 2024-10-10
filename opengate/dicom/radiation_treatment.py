import os
import itk
import numpy as np
import pydicom
import logging
import re

from .roi_utils import region_of_interest
from .helpers_dcm import bounding_box, crop_and_pad_image


logger = logging.getLogger(__name__)

class radiation_treatment:
    # NOTE: we assume that all dcm files concerning a specific plan are in the sane folder
    # Dicom consistency is checked when creating the correspondent object
    def __init__(self, rp_path, clinical=True):
        self.dcm_dir = os.path.dirname(rp_path)  # directory with all dicom files

        # RT plan as beamset_info object
        print("Get RP file")
        self.rp_path = rp_path
        self.beamset_info = BeamsetInfo(rp_path)
        self.uid = self.beamset_info.uid  # same for all files
        self.beams = self.beamset_info.beams
        self.isocenters = [b.IsoCenter for b in self.beams]

        # RT doses: dictionary with dose info for each RD file. One RD for each beam
        print("----------------------------")
        print("Get RD files")
        self.rt_doses = dose_info.get_dose_files(
            self.dcm_dir, self.uid, clinical=clinical
        )

        # RT structures
        print("----------------------------")
        print("Get RS file")
        self.ss_ref_uid = self.beamset_info.structure_set_uid
        self.structures = RT_structs(self.dcm_dir, self.ss_ref_uid)
        self.structures_dcm = self.structures.structure_set

        # CT
        print("----------------------------")
        print("Get CT files")
        self.ctuid = (
            self.structures_dcm.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )

        _, ct_files = get_series_filenames(self.dcm_dir, self.ctuid)
        self.ct_image = ct_image_from_dicom(ct_files, self.ctuid)

    def preprocess_ct(self, enforce_air_outside_ext=True):
        ct_orig = self.ct_image.img
        ct_array = self.ct_image.array

        # dose grid info
        plan_dose = self.rt_doses["PLAN"]

        # overriding voxels outside external ROI with G4_AIR
        ct_hu_overrides = ct_orig
        if enforce_air_outside_ext:
            ext_roi = region_of_interest(
                ds=self.structures_dcm, roi_id=self.structures.external
            )
            ext_mask = ext_roi.get_mask(ct_orig, corrected=False)
            ext_array = itk.GetArrayViewFromImage(ext_mask) > 0
            ct_array[np.logical_not(ext_array)] = -1000  # hu_air
            ct_hu_overrides = itk.GetImageFromArray(ct_array)
            ct_hu_overrides.CopyInformation(ct_orig)

        # crop CT
        bb_ct = bounding_box(img=ct_hu_overrides)
        bb_dose = bounding_box(img=plan_dose.image)
        ct_padded = ct_hu_overrides
        if not bb_dose in bb_ct:
            print("dose matrix IS NOT contained in original CT! adding dose padding")
            bb_dose_padding = bounding_box(bb=bb_ct)
            bb_dose_padding.merge(bb_dose)
            # ibbmin = np.array(ct_hu_overrides.TransformPhysicalPointToIndex(bb_dose_padding.mincorner))
            # ibbmax = np.array(ct_hu_overrides.TransformPhysicalPointToIndex(bb_dose_padding.maxcorner))+1
            ibbmin, ibbmax = bb_dose_padding.indices_in_image(ct_hu_overrides)
            ct_padded = crop_and_pad_image(
                ct_hu_overrides, ibbmin, ibbmax, -1000
            )  # "air" padding
        # ibbmin,ibbmax = bb_ct.indices_in_image(ct_padded)
        # ct_cropped = gate.crop_and_pad_image(ct_padded,ibbmin,ibbmax,-100) # "air" padding
        ct_cropped = ct_padded
        # new ct grid
        self.preprocessed_ct = ct_image_from_mhd(ct_cropped)

        return self.preprocessed_ct

def get_container_size(itk_img, isocenter):
    ct_bb = bounding_box(img=itk_img)
    rot_box_size = 2.0001 * np.max(
        np.abs(
            np.stack(
                [ct_bb.mincorner - isocenter, ct_bb.maxcorner - isocenter]
            )
        ),
        axis=0,
    )

    return list(rot_box_size)
    
class ct_image_base:
    @property
    def meta_data(self):
        slicetimes = [int(s.get("InstanceCreationTime", "0")) for s in self._slices]
        return {
            "Institution Name": str(
                self._slices[0].get("InstitutionName", "anonymized")
            ),
            "Series Instance UID": self._uid,
            "Creation Date": str(
                self._slices[0].get("InstanceCreationDate", "anonymized")
            ),
            "Imaging time": "{}-{}".format(min(slicetimes), max(slicetimes)),
            "NVoxelsXYZ": tuple(self.size.tolist()),
            "NVoxelsTOT": np.prod(self.array.shape),
            "Resolution [mm]": tuple(self.voxel_size.tolist()),
            "Origin [mm]": tuple(self.origin.tolist()),
            "Center [mm]": tuple(
                (self.origin + 0.5 * (self.size - 1) * self.voxel_size).tolist()
            ),
        }

    @property
    def img(self):
        # TODO: should we return a copy or a reference?
        return self._img

    @property
    def nvoxels(self):  # already correct order: [x,y,z]
        # more intuitive name than 'size'
        return np.array(self._img.GetLargestPossibleRegion().GetSize())

    @property
    def size(self):
        return np.array(self._img.GetLargestPossibleRegion().GetSize())

    @property
    def physical_size(self):
        return self.size * np.array(self._img.GetSpacing())

    @property
    def voxel_size(self):
        return np.array(self._img.GetSpacing())

    @property
    def origin(self):
        return np.array(self._img.GetOrigin())

    @property
    def array(self):
        return self._img_array

    @property
    def slices(self):
        return self._slices

    @property
    def uid(self):
        return str(self._slices[0].SeriesInstanceUID)

    def write_to_file(self, mhd):
        assert mhd[-4:].lower() == ".mhd"
        itk.imwrite(self._img, mhd)


class ct_image_from_mhd(ct_image_base):
    def __init__(self, img):
        self._img = img


class ct_image_from_dicom(ct_image_base):
    def __init__(self, flist, uid):
        print(
            "got {} CT files, first={} last={}".format(len(flist), flist[0], flist[-1])
        )
        self._slices = [pydicom.dcmread(f) for f in flist]
        print("got {} CT slices".format(len(self._slices)))

        # check slices integrity
        self._check_dcm_slices()

        # sort slices according to their position along the axis
        self._slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
        slice_thicknesses = np.round(
            np.diff([s.ImagePositionPatient[2] for s in self._slices]), decimals=2
        )

        # get spacing -> [sx, sy, sz] average size of all ct slices
        pixel_widths = np.round([s.PixelSpacing[1] for s in self._slices], decimals=2)
        pixel_heights = np.round([s.PixelSpacing[0] for s in self._slices], decimals=2)
        spacing = []
        print("going to obtain voxel spacing")
        for sname, spacings in zip(
            ["pixel width", "pixel height", "slice thickness"],
            [pixel_widths, pixel_heights, slice_thicknesses],
        ):
            if 1 < len(set(spacings)):
                # TO DO: define rounding error tolerance
                print(
                    "The {} seems to suffer from rounding issues (or missing slices): min={} mean={} median={} std={} max={}".format(
                        sname,
                        np.min(spacings),
                        np.mean(spacings),
                        np.median(spacings),
                        np.std(spacings),
                        np.max(spacings),
                    )
                )
            spacing.append(np.mean(spacings))
        print("spacing is ({},{},{})".format(*spacing))

        # get origin
        origin = self._slices[0].ImagePositionPatient[:]
        print("origin is ({},{},{})".format(*origin))

        # TODO: is it possible that some self._slices have a different intercept and slope?
        intercept = np.int16(self._slices[0].RescaleIntercept)
        slope = np.float64(self._slices[0].RescaleSlope)
        print("HU rescale: slope={}, intercept={}".format(slope, intercept))

        # stack 2D slices together to get 3D pixel array
        if slope != 1:
            self._img_array = np.stack([s.pixel_array for s in self._slices]).astype(
                np.int16
            )
            self._img_array = (slope * self._img_array).astype(np.int16) + intercept
        else:
            self._img_array = (
                np.stack([s.pixel_array for s in self._slices]).astype(np.int16)
                + intercept
            )
        print(
            "after HU rescale: min={}, mean={}, median={}, max={}".format(
                np.min(self._img_array),
                np.mean(self._img_array),
                np.median(self._img_array),
                np.max(self._img_array),
            )
        )

        # set image properties
        self._img = itk.GetImageFromArray(self._img_array)
        self._img.SetSpacing(tuple(spacing))
        self._img.SetOrigin(tuple(origin))
        self._uid = uid

    def _check_dcm_slices(self):
        for dcm in self._slices:
            genericTags = [
                "InstanceCreationDate",
                "SeriesInstanceUID",
                "ImagePositionPatient",
                "RescaleIntercept",
                "RescaleSlope",
                "InstanceCreationTime",
                "ImagePositionPatient",
                "PixelSpacing",
            ]
            missing_keys = []
            for key in genericTags:
                if key not in dcm:
                    missing_keys.append(key)
            if missing_keys:
                raise ImportError(
                    "DICOM CT file not conform. Missing keys: ", missing_keys
                )
        print("\033[92mCT files ok \033[0m")


def get_series_filenames(ddir, uid=None):
    dcmseries_reader = itk.GDCMSeriesFileNames.New(Directory=ddir)
    ids = dcmseries_reader.GetSeriesUIDs()
    print("got DICOM {} series IDs".format(len(ids)))
    flist = list()
    if uid:
        if uid in ids:
            try:
                # flist = sitk.ImageSeriesReader_GetGDCMSeriesFileNames(ddir,uid)
                flist = dcmseries_reader.GetFileNames(uid)
                return uid, flist
            except:
                print(
                    "something wrong with series uid={} in directory {}".format(
                        uid, ddir
                    )
                )
                raise
    else:
        ctid = list()
        for suid in ids:
            # flist = sitk.ImageSeriesReader_GetGDCMSeriesFileNames(ddir,suid)
            flist = dcmseries_reader.GetFileNames(suid)
            f0 = pydicom.dcmread(flist[0])
            if not hasattr(f0, "SOPClassUID"):
                print(
                    "weird, file {} has no SOPClassUID".format(
                        os.path.basename(flist[0])
                    )
                )
                continue
            descr = pydicom.uid.UID_dictionary[f0.SOPClassUID][0]
            if descr == "CT Image Storage":
                print("found CT series id {}".format(suid))
                ctid.append(suid)
            else:
                print('not CT: series id {} is a "{}"'.format(suid, descr))
        if len(ctid) > 1:
            raise ValueError(
                "no series UID was given, and I found {} different CT image series: {}".format(
                    len(ctid), ",".join(ctid)
                )
            )
        elif len(ctid) == 1:
            uid = ctid[0]
            # flist = sitk.ImageSeriesReader_GetGDCMSeriesFileNames(ddir,uid)
            flist = dcmseries_reader.GetFileNames(uid)
            return uid, flist
        
class dose_info(object):
    def __init__(self, rd, rdfp):
        self._rd = rd
        self._rdfp = rdfp
        try:
            # beam dose
            self._beamnr = str(
                self._rd.ReferencedRTPlanSequence[0]
                .ReferencedFractionGroupSequence[0]
                .ReferencedBeamSequence[0]
                .ReferencedBeamNumber
            )
        except:
            # plan dose
            self._beamnr = None
        assert self._rd.pixel_array.shape == (
            int(self._rd.NumberOfFrames),
            int(self._rd.Rows),
            int(self._rd.Columns),
        )

    @property
    def filepath(self):
        return self._rdfp

    @property
    def image(self):
        scaling = float(self._rd.DoseGridScaling)
        img = itk.GetImageFromArray(self._rd.pixel_array * scaling)
        img.SetOrigin(self.origin)
        img.SetSpacing(self.spacing)
        return img

    @property
    def ref_uid(self):
        return str(self._rd.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID)

    @property
    def spacing(self):
        return np.array(
            [float(v) for v in self._rd.PixelSpacing[::-1] + [self._rd.SliceThickness]]
        )

    @property
    def center(self):
        return self.origin - 0.5 * self.spacing + 0.5 * self.physical_size

    @property
    def physical_size(self):
        return self.spacing * self.nvoxels

    @property
    def nvoxels(self):
        return np.array(self._rd.pixel_array.shape[::-1])

    @property
    def origin(self):
        return np.array([float(v) for v in self._rd.ImagePositionPatient])

    @property
    def is_physical(self):
        return str(self._rd.DoseType).upper() == "PHYSICAL"

    @property
    def is_effective(self):
        return str(self._rd.DoseType).upper() == "EFFECTIVE"

    @property
    def is_beam_dose(self):
        return self._beamnr is not None

    @property
    def is_plan_dose(self):
        return self._beamnr is None

    @property
    def refd_beam_number(self):
        return self._beamnr

    @property
    def dicom_obj(self):
        return self._rd

    @staticmethod
    def get_dose_files(dirpath, rpuid=None, only_physical=False, clinical=True):
        doses = dict()
        # beam_numbers = [str(beam.BeamNumber) for beam in self._rp.IonBeamSequence]
        print("going to find RD dose files in directory {}".format(dirpath))
        print("for UID={} PLAN".format(rpuid if rpuid else "any/all"))
        for s in os.listdir(dirpath):
            if not s[-4:].lower() == ".dcm":
                print("NOT DICOM (no dcm suffix): {}".format(s))
                continue  # not dicom
            fpath = os.path.join(dirpath, s)
            dcm = pydicom.dcmread(fpath)
            if "SOPClassUID" not in dcm:
                continue  # not a RD dose file
            if dcm.SOPClassUID.name != "RT Dose Storage":
                continue  # not a RD dose file

            dose_type = str(dcm.DoseType).upper()
            dose_sum_type = str(dcm.DoseSummationType)

            if clinical:
                # check file integrity
                check_file(dcm)

                drefrtp0 = dcm.ReferencedRTPlanSequence[0]
                if rpuid:
                    uid = str(drefrtp0.ReferencedSOPInstanceUID)
                    if uid != rpuid:
                        print("UID {} != RP UID {}".format(uid, rpuid))
                        continue  # dose file for a different plan

                if dose_sum_type.upper() == "PLAN":
                    # the physical or effective plan dose file (hopefully)
                    label = "PLAN"
                else:
                    # a beam dose file (hopefully)
                    label = str(
                        drefrtp0.ReferencedFractionGroupSequence[0]
                        .ReferencedBeamSequence[0]
                        .ReferencedBeamNumber
                    )
                    print("BEAM DOSE FILE FOR {}".format(label))
            else:
                if dose_sum_type.upper() == "PLAN":
                    # the physical or effective plan dose file (hopefully)
                    label = "PLAN"
                else:
                    label = dose_type

            if dose_type == "EFFECTIVE":
                print("got EFFECTIVE=RBE dose for {}".format(label))
                label += "_RBE"
            elif dose_type == "PHYSICAL":
                print("got PHYSICAL dose for {}".format(label))
            else:
                raise RuntimeError(
                    "unknown dose type {} for {} dose, UID={}".format(
                        dose_type, label, uid
                    )
                )
            if label in doses.keys():
                # oopsie!
                raise RuntimeError(
                    "multiple dose files for beamnr/plan={} and UID={}".format(
                        label, uid
                    )
                )
            if dose_type == "PHYSICAL" or not only_physical:
                doses[label] = dose_info(dcm, fpath)
        # if we arrive here, things are probably fine...
        return doses


def loop_over_tags_level(tags, data, missing_keys):
    for key in tags:
        if key not in data:
            missing_keys.append(key)


def check_file(dcm):
    genericTags = [
        "NumberOfFrames",
        "ReferencedRTPlanSequence",
        "Rows",
        "Columns",
        "DoseGridScaling",
        "PixelSpacing",
        "SliceThickness",
        "ImagePositionPatient",
        "DoseType",
        "SOPClassUID",
        "DoseSummationType",
        "DoseUnits",
    ]

    planSeqTag = [
        "ReferencedSOPInstanceUID"
    ]  # "ReferencedFractionGroupSequence" only if "DoseSummationType" == PLAN
    refBeamTag = "ReferencedBeamNumber"
    missing_keys = []

    # check first layer of the hierarchy
    loop_over_tags_level(genericTags, dcm, missing_keys)

    # check referenced RT Plan seq
    if "ReferencedRTPlanSequence" in dcm:
        # check ROI contour sequence
        loop_over_tags_level(planSeqTag, dcm.ReferencedRTPlanSequence[0], missing_keys)

        if "DoseSummationType" in dcm:
            if dcm.DoseSummationType != "PLAN":
                # check also ReferencedFractionGroupSequence
                if (
                    "ReferencedFractionGroupSequence"
                    not in dcm.ReferencedRTPlanSequence[0]
                ):
                    missing_keys.append("ReferencedFractionGroupSequence")
                elif (
                    refBeamTag
                    not in dcm.ReferencedRTPlanSequence[0]
                    .ReferencedFractionGroupSequence[0]
                    .ReferencedBeamSequence[0]
                ):
                    missing_keys.append(
                        "ReferencedBeamNumber under ReferencedRTPlanSequence/ReferencedFractionGroupSequence/ReferencedBeamSequence"
                    )

    if missing_keys:
        raise ImportError("DICOM RD file not conform. Missing keys: ", missing_keys)
    else:
        print("\033[92mRD file ok \033[0m")
        
def is_close(x, y, eps=1e-6):
    sumabs = np.abs(x) + np.abs(y)
    absdif = np.abs(x - y)
    ok = (sumabs == 0) or (absdif < eps * 0.5 * sumabs)
    return ok


def sequence_check(obj, attr, nmin=1, nmax=0, name="object"):
    logger.debug("checking that {} has attribute {}".format(name, attr))
    assert hasattr(obj, attr)
    seq = getattr(obj, attr)
    logger.debug(
        "{} has length {}, will check if it >={} and <={}".format(
            name, len(seq), nmin, nmax
        )
    )
    assert len(seq) >= nmin
    assert nmax == 0 or len(seq) <= nmax


def spots_info_from_txt(txtFile, ionType, beam_nr):
    # initialize empty variables
    nFields = 0
    n_beam = 0
    energies = []
    nSpots = []
    spots = []
    start_index = []
    G = 0
    found_field = False

    # read  content
    with open(txtFile, "r") as f:
        lines = f.readlines()

    # get plan's info
    # TODO: make function to check line tag
    for i, line in enumerate(lines):
        if check_plan_tag(line, "NumberOfFields"):
            l = lines[i + 1].split("\n")[0]
            nFields = int(l)
            if beam_nr > nFields:
                raise ValueError(
                    "requested beam number higher than number of beams in the beamset"
                )
        if check_plan_tag(line, "FIELD-DESCRIPTION"):
            found_field = False
        if check_plan_tag(line, "FieldID"):
            fieldID = int(lines[i + 1].split("\n")[0])
            if fieldID == beam_nr:
                found_field = True
        if found_field:
            if check_plan_tag(line, "GantryAngle"):
                l = lines[i + 1].split("\n")[0]
                G = int(l)
            if check_plan_tag(line, "FinalCumulativeMeterSetWeight"):
                l = lines[i + 1].split("\n")[0]
                n_beam = float(l)
            if check_plan_tag(line, "Energy"):
                l = lines[i + 1].split("\n")[0]
                energies.append(float(l))
            if check_plan_tag(line, "NbOfScannedSpots"):
                l = lines[i + 1].split("\n")[0]
                nSpots.append(int(l))
            if check_plan_tag(line, "X Y Weight"):
                start_index.append(i + 1)

    for i in range(len(energies)):
        e = energies[i]
        # print(f"ENERGY: {e}")
        start = start_index[i]
        end = start_index[i] + nSpots[i]
        for j in range(start, end):
            l = lines[j].split("\n")[0].split()
            spot = SpotInfo(float(l[0]), float(l[1]), float(l[2]), e)
            spot.beamFraction = float(l[2]) / n_beam
            spot.particle_name = ionType
            spots.append(spot)

    return spots, n_beam, energies, G


def check_plan_tag(txt_line, tag):
    txt_line = txt_line.strip().lower()
    tag = tag.strip().lower()
    return tag in txt_line


def get_spots_from_beamset(beamset):
    rad_type = beamset.bs_info["Radiation Type Opengate"]
    spots_array = []
    mswtot = beamset.mswtot
    for beam in beamset.beams:
        # mswtot = beam.mswtot
        for energy_layer in beam.layers:
            for spot in energy_layer.spots:
                nPlannedSpot = spot.w
                spot.beamFraction = (
                    nPlannedSpot / mswtot
                )  # nr particles planned for the spot/tot particles planned for the beam
                spot.particle_name = rad_type
                spots_array.append(spot)
    return spots_array


def get_spots_from_beamset_beam(beamset, beam_nr):
    rad_type = beamset.bs_info["Radiation Type Opengate"]
    spots_array = []
    beam = beamset.beams[beam_nr]
    mswtot = beam.mswtot
    for energy_layer in beam.layers:
        for spot in energy_layer.spots:
            nPlannedSpot = spot.w
            spot.beamFraction = (
                nPlannedSpot / mswtot
            )  # nr particles planned for the spot/tot particles planned for the beam
            spot.particle_name = rad_type
            spots_array.append(spot)
    return spots_array


# FIXME: IonSpotInfo
class SpotInfo(object):
    def __init__(self, xiec, yiec, w, e):
        self.xiec = xiec
        self.yiec = yiec
        self.w = w
        self.energy = e
        self.particle_name = None
        self.beamFraction = None
        self.t0 = None
        self.t1 = None

    def get_msw(self, t0, t1):
        return self.w


class LayerInfo(object):
    def __init__(self, ctrlpnt, j, cumsumchk=[], verbose=False, keep0=False):
        self._cp = ctrlpnt
        if verbose:
            logger.debug("{}. control point with type {}".format(j, type(self._cp)))
            for k in self._cp.keys():
                if pydicom.datadict.dictionary_has_tag(k):
                    kw = pydicom.datadict.keyword_for_tag(k)
                else:
                    kw = "(UNKNOWN)"
                logger.debug("k={} keyword={}".format(k, kw))
        nspot = int(self._cp.NumberOfScanSpotPositions)
        # assert(self._cp.NominalBeamEnergyUnit == 'MEV')
        if nspot == 1:
            self.w = np.array([float(self._cp.ScanSpotMetersetWeights)])
        else:
            self.w = np.array([float(w) for w in self._cp.ScanSpotMetersetWeights])
        assert nspot == len(self.w)
        assert nspot * 2 == len(self._cp.ScanSpotPositionMap)
        # self.cpindex = int(self._cp.ControlPointIndex)
        # self.spotID = str(self._cp.ScanSpotTuneID)
        cmsw = float(self._cp.CumulativeMetersetWeight)
        if cumsumchk:
            logger.debug(
                "CumulativeMetersetWeight={0:14.8g} sum of previous spots={1:14.8g} diff={2:14.8g}".format(
                    cmsw, cumsumchk[0], cmsw - cumsumchk[0]
                )
            )
            assert is_close(cmsw, cumsumchk[0])
        # self.npainting = int(self._cp.NumberOfPaintings)
        xy = np.array([float(pos) for pos in self._cp.ScanSpotPositionMap]).reshape(
            nspot, 2
        )
        self.x = np.array(xy[:, 0])
        self.y = np.array(xy[:, 1])
        if not keep0:
            mask = self.w > 0.0
            self.w = self.w[mask]
            self.x = self.x[mask]
            self.y = self.y[mask]

        wsum = np.sum(self.w)
        logger.debug(
            "layer number {} has {} spots, of which {} with zero weight, cumsum={}, sum(w)={}".format(
                j, len(self.w), np.sum(self.w <= 0), cmsw, wsum
            )
        )

        cumsumchk[0] += wsum

    @property
    def energy(self):
        # DICOM specifies energy per nucleon, Gate wants total kinetic energy
        return float(self._cp.NominalBeamEnergy)

    @property
    def tuneID(self):
        return str(self._cp.ScanSpotTuneID)

    @property
    def npainting(self):
        return int(self._cp.NumberOfPaintings)

    @property
    def mswtot(self):
        return np.sum(self.w)

    @property
    def nspots(self):
        return len(self.w)

    @property
    def weights(self):
        return self.w

    @property
    def spots(self):
        e = self.energy
        return [SpotInfo(x, y, w, e) for (x, y, w) in zip(self.x, self.y, self.w)]

    def get_spots(self, t0=None, t1=None):
        e = self.energy
        return [SpotInfo(x, y, w, e) for (x, y, w) in zip(self.x, self.y, self.w)]


class BeamInfo(object):
    # def __init__(self,beam,rd,i,keep0=False):
    def __init__(self, beam, i, override_number, keep0=False):
        logger.debug("loading {}th beam".format(i))
        self._dcmbeam = beam  # the DICOM beam object
        self._warnings = list()  # will hopefully stay empty
        logger.debug("trying to access first control point")
        self._icp0 = beam.IonControlPointSequence[0]  # convenience: first control point
        self._beam_number_is_fishy = (
            override_number  # workaround for buggy TPSs, e.g. PDM
        )
        self._index = i  # the index in the beam sequence
        self._layers = list()
        mswchk = self.FinalCumulativeMetersetWeight
        cumsumchk = [0.0]
        logger.debug("going to read all layers")
        for j, icp in enumerate(self._dcmbeam.IonControlPointSequence):
            li = LayerInfo(icp, j, cumsumchk, False, keep0)
            if 0.0 < li.mswtot or keep0:
                self._layers.append(li)
        logger.debug("survived reading all layers")
        if not is_close(mswchk, cumsumchk[0]):
            raise ValueError(
                "final cumulative msw {} != sum of spot msw {}".format(
                    mswchk, cumsumchk[0]
                )
            )
        logger.debug("survived cumulative MSW check")

    def GetAndClearWarnings(self):
        # return and clear
        w = self._warnings[:]
        self._warnings = list()
        return w

    @property
    def FinalCumulativeMetersetWeight(self):
        return float(self._dcmbeam.FinalCumulativeMetersetWeight)

    @property
    def PatientSupportAngle(self):
        return float(self._icp0.PatientSupportAngle)

    @property
    def patient_angle(self):
        return float(self._icp0.PatientSupportAngle)

    @property
    def IsoCenter(self):
        if "IsocenterPosition" in self._icp0:
            if len(self._icp0.IsocenterPosition) == 3.0:
                return [float(xyz) for xyz in self._icp0.IsocenterPosition]
            else:
                msg = "Got corrupted isocenter = '{}'; assuming [0,0,0] for now, keep fingers crossed.".format(
                    self._icp0.IsocenterPosition
                )
        else:
            msg = "No isocenter specified in treatment plan; assuming [0,0,0] for now, keep fingers crossed."
        logger.error(msg)
        self._warnings.append(msg)
        # FIXME: what to do else? Cry? Throw segfaults? Drink bad coffee?
        return [0.0, 0.0, 0.0]

    @property
    def Name(self):
        # TODO: the Name and name properties are identical, keep only one of them.
        return str(self._dcmbeam.BeamName)

    @property
    def Number(self):
        # TODO: the Number and number properties are identical, keep only one of them.
        nr = (
            str(self._index + 1)
            if self._beam_number_is_fishy
            else str(self._dcmbeam.BeamNumber)
        )
        return nr

    @property
    def name(self):
        # TODO: the Name and name properties are identical, keep only one of them.
        return str(self._dcmbeam.BeamName)

    @property
    def number(self):
        # TODO: the Number and number properties are identical, keep only one of them.
        nr = (
            str(self._index + 1)
            if self._beam_number_is_fishy
            else str(self._dcmbeam.BeamNumber)
        )
        return nr

    @property
    def RadiationType(self):
        radtype = str(self._dcmbeam.RadiationType)
        radtypeOpengate = None
        if radtype == "ION":
            ionZ = str(self._dcmbeam.RadiationAtomicNumber)
            ionA = str(self._dcmbeam.RadiationMassNumber)
            ionQ = str(self._dcmbeam.RadiationChargeState)
            radtype = "_".join(["ION", ionZ, ionA, ionQ])
            radtypeOpengate = f"ion {ionZ} {ionA}"
        return [radtype, radtypeOpengate]

    @property
    def gantry_angle(self):
        return float(self._icp0.GantryAngle)

    @property
    def TreatmentMachineName(self):
        if "TreatmentMachineName" in self._dcmbeam:
            return str(self._dcmbeam.TreatmentMachineName)
        # RayStation 8b exports anonymized treatment plans without the treatment machine name!
        if np.isclose(self.gantry_angle, 0.0):
            # FIXME: should be solved in a way that works for any clinic, not just MedAustron
            ducktape = str("IR2VBL")
        elif np.isclose(self.gantry_angle, 90.0):
            # FIXME: should be solved in a way that works for any clinic, not just MedAustron
            ducktape = str("IR2HBL")
        else:
            raise ValueError(
                "treatment machine name is missing and gantry angle {} does not enable a good guess".format(
                    self.gantry_angle
                )
            )
        msg = "treatment machine name for beam name={} number={} missing in treatment plan, guessing '{}' from gantry angle {}".format(
            self.name, self.number, ducktape, self.gantry_angle
        )
        logger.error(msg)
        self._warnings.append(msg)
        return ducktape  # ugly workaround! FIXME!

    @property
    def SnoutID(self):
        if "SnoutSequence" in self._dcmbeam:
            return str(self._dcmbeam.SnoutSequence[0].SnoutID)
        # FIXME: what to do else?
        return str("NA")

    @property
    def SnoutPosition(self):
        if "SnoutPosition" in self._dcmbeam:
            return float(self._icp0.SnoutPosition)
        # FIXME: what to do else?
        return str("NA")

    @property
    def NumberOfRangeModulators(self):
        return int(self._dcmbeam.NumberOfRangeModulators)

    @property
    def RangeModulatorIDs(self):
        if self.NumberOfRangeModulators > 0:
            return [rm.RangeModulatorID for rm in self._dcmbeam.RangeModulatorSequence]
        return list()

    @property
    def NumberOfRangeShifters(self):
        return int(self._dcmbeam.NumberOfRangeShifters)

    @property
    def RangeShifterIDs(self):
        if self.NumberOfRangeShifters > 0:
            return [str(rs.RangeShifterID) for rs in self._dcmbeam.RangeShifterSequence]
        return list()

    @property
    def NumberOfEnergies(self):
        return len(
            set(
                [icp.NominalBeamEnergy for icp in self._dcmbeam.IonControlPointSequence]
            )
        )

    @property
    def nlayers(self):
        return len(self._layers)

    @property
    def layers(self):
        return self._layers

    @property
    def nspots(self):
        return sum([l.nspots for l in self.layers])

    @property
    def mswtot(self):
        return sum([l.mswtot for l in self._layers])

    @property
    def PrimaryDosimeterUnit(self):
        return str(self._dcmbeam.PrimaryDosimeterUnit)


class BeamsetInfo(object):
    """
    This class reads a DICOM 'RT Ion Plan Storage' file and collects related information such as TPS dose files.
    It does NOT (yet) try to read a reffered structure set and/or CT images.
    This acts as a wrapper (all DICOM access on the plan file happens here). This has a few advantages over direct
    DICOM access in the other modules:
    * we can deal with different "DICOM dialects" here; some TPSs may store their plans in different ways.
    * if 'private tags' need to be taken into account then we can also do that here.
    * We can make a similar class, with the same attributes, for a treatment plan stored in a different format, e.g. for research, commissioning or QA purposes.

    Then the rest of the code can work with that in the same way.
    """

    patient_attrs = ["Patient ID", "Patient Name", "Patient Birth Date", "Patient Sex"]
    plan_req_attrs = [
        "RT Plan Label",
        "SOP Instance UID",
        "Referring Physician Name",
        "Plan Intent",
    ]
    plan_opt_attrs = ["Operators Name", "Reviewer Name", "Review Date", "Review Time"]
    plan_attrs = plan_req_attrs + plan_opt_attrs
    bs_attrs = [
        "Number Of Beams",
        "RT Plan Label",
        "Prescription Dose",
        "Target ROI Name",
        "Radiation Type",
        "Treatment Machine(s)",
    ]

    def __init__(self, rpfp):
        self._warnings = list()  # will hopefully stay empty
        self._beam_numbers_corrupt = False  # e.g. PDM does not define beam numbers
        self._rp = pydicom.dcmread(rpfp)
        self._rpfp = rpfp
        logger.debug("beamset: survived reading DICOM file {}".format(rpfp))
        self._rpdir = os.path.dirname(rpfp)
        self._rpuid = str(self._rp.SOPInstanceUID)
        self._dose_roiname = (
            None  # stays None for CT-less plans, e.g. commissioning plans
        )
        self._dose_roinumber = (
            None  # stays None for CT-less plans, e.g. commissioning plans
        )
        logger.debug("beamset: going to do some checks")
        self._chkrp()
        logger.debug("beamset: survived check, loading beams")
        self._beams = [
            BeamInfo(b, i, self._beam_numbers_corrupt)
            for i, b in enumerate(self._rp.IonBeamSequence)
        ]
        logger.debug("beamset: DONE")

    def GetAndClearWarnings(self):
        # return a copy
        for b in self._beams:
            # bwarnings = b.GetAndClearWarnings()
            for w in b.GetAndClearWarnings():
                if w not in self._warnings:
                    self._warnings.append(w)
        allw = self._warnings[:]
        self._warnings = list()
        return allw

    def __getitem__(self, k):
        if type(k) == int:
            if k >= 0 and k < len(self._beams):
                return self._beams[k]
            else:
                raise IndexError(
                    "attempt to get nonexisting beam with index {}".format(k)
                )
        for b in self._beams:
            if str(k) == b.name or str(k) == b.number:
                return b
        raise KeyError("attempt to get nonexisting beam with key {}".format(k))

    def _chkrp(self):
        if "SOPClassUID" not in self._rp:
            raise IOError("bad DICOM file {},\nmissing SOPClassUID".format(self._rpfp))
        sop_class_name = pydicom.uid.UID_dictionary[self._rp.SOPClassUID][0]
        if sop_class_name != "RT Ion Plan Storage":
            raise IOError(
                "bad plan file {},\nwrong SOPClassUID: {}='{}',\nexpecting an 'RT Ion Plan Storage' file instead.".format(
                    self._rpfp, self._rp.SOPClassUID, sop_class_name
                )
            )
        missing_attrs = list()
        for a in ["IonBeamSequence"] + self.plan_req_attrs + self.patient_attrs:
            b = a.replace(" ", "")
            if not hasattr(self._rp, b):
                missing_attrs.append(b)
        if missing_attrs:
            raise IOError(
                "bad plan file {},\nmissing keys: {}".format(
                    self._rpfp, ", ".join(missing_attrs)
                )
            )
        # self._get_rds()
        if hasattr(self._rp, "DoseReferenceSequence"):
            sequence_check(self._rp, "DoseReferenceSequence", 1, 1)
            if hasattr(self._rp.DoseReferenceSequence[0], "ReferencedROINumber"):
                self._dose_roinumber = int(
                    self._rp.DoseReferenceSequence[0].ReferencedROINumber
                )
        if self._dose_roinumber is None:
            logger.info(
                "no target ROI specified (probably because of missing DoseReferenceSequence)"
            )
        sequence_check(self._rp, "IonBeamSequence", 1, 0)
        sequence_check(self._rp, "FractionGroupSequence", 1, 1)
        frac0 = self._rp.FractionGroupSequence[0]
        sequence_check(
            frac0,
            "ReferencedBeamSequence",
            len(self._rp.IonBeamSequence),
            len(self._rp.IonBeamSequence),
        )
        number_set = set()
        for dcmbeam in self._rp.IonBeamSequence:
            nr = int(dcmbeam.BeamNumber)
            if nr < 0:
                self._beam_numbers_corrupt = True
                logger.error(
                    "CORRUPT INPUT: found a negative beam number {}.".format(nr)
                )
            if nr in number_set:
                self._beam_numbers_corrupt = True
                logger.error(
                    "CORRUPT INPUT: found same beam number {} for multiple beams.".format(
                        nr
                    )
                )
            number_set.add(nr)
        if self._beam_numbers_corrupt:
            msg = "Beam numbers are corrupt! Will override them with simple enumeration, keep fingers crossed."
            logger.error(msg)
            self._warnings.append(msg)
        logger.debug("checked planfile, looks like all attributes are available...")
    
    @property
    def structure_set_uid(self):
        return self._rp.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID

    @property
    def mswtot(self):
        return sum([b.mswtot for b in self._beams])

    @property
    def name(self):
        # It looks like RTPlanLabel is for the beamset,
        # and RTPlanName is for the entire plan including possibly several beamsets.
        # the RTPlanName is not exported anymore in RayStation 8b, so let's forget about the plan name
        # some anonymization methods are butchering all useful labeling information, even the label and name of an RT plan.
        return str(self._rp.get("RTPlanLabel", "anonymized"))

    @property
    def fields(self):
        # GATE synomym for 'beams'
        return self._beams

    @property
    def beams(self):
        return self._beams

    @property
    def uid(self):
        return self._rpuid

    @property
    def beam_angles(self):
        return [str(bm.gantry_angle) for bm in self._beams]

    @property
    def beam_names(self):
        return [str(bm.Name) for bm in self._beams]

    @property
    def beam_numbers(self):
        return [str(bm.Number) for bm in self._beams]

    @property
    def Nfractions(self):
        # FIXME: some evil DICOM plan files have "NumberOfFractionsPlanned" equal to zero. Force this to be one, or is this zero somehow meaningful & useful?
        nfrac = int(self._rp.FractionGroupSequence[0].NumberOfFractionsPlanned)
        if nfrac > 0:
            return nfrac
        logger.error("Got Nfractions={} ???! Using nfrac=1 instead.".format(nfrac))
        return 1

    @property
    def target_ROI_name(self):
        return self._dose_roiname

    @target_ROI_name.setter
    def target_ROI_name(self, roiname):
        self._dose_roiname = roiname

    @property
    def target_ROI_number(self):
        return self._dose_roinumber

    @property
    def prescription_dose(self):
        if hasattr(self._rp, "DoseReferenceSequence"):
            if hasattr(self._rp.DoseReferenceSequence[0], "TargetPrescriptionDose"):
                return float(self._rp.DoseReferenceSequence[0].TargetPrescriptionDose)
        return "NA"

    @property
    def plan_label(self):
        return str(self._rp.get("RTPlanLabel", "anonymized"))

    @property
    def sanitized_plan_label(self):
        badchars = re.compile("[^a-zA-Z0-9_]")
        return re.sub(badchars, "_", self.plan_label)

    @property
    def patient_info(self):
        return dict(
            [
                (a, str(getattr(self._rp, a.replace(" ", ""))))
                for a in self.patient_attrs
            ]
        )

    @property
    def plan_info(self):
        reqs = dict(
            [
                (a, str(getattr(self._rp, a.replace(" ", ""))))
                for a in self.plan_req_attrs
            ]
        )
        opts = dict(
            [
                (
                    a,
                    "NA"
                    if not hasattr(self._rp, a.replace(" ", ""))
                    else str(getattr(self._rp, a.replace(" ", ""))),
                )
                for a in self.plan_opt_attrs
            ]
        )
        reqs.update(opts)
        return reqs

    @property
    def bs_info(self):
        info = dict(
            [
                ("Number Of Beams", str(len(self._beams))),
                ("RT Plan Label", self.plan_label),
                ("Prescription Dose", str(self.prescription_dose)),
                ("Target ROI Name", str(self.target_ROI_name)),
                (
                    "Radiation Type",
                    ", ".join(
                        set([str(beam.RadiationType[0]) for beam in self._beams])
                    ),
                ),
                (
                    "Radiation Type Opengate",
                    ", ".join(
                        set([str(beam.RadiationType[1]) for beam in self._beams])
                    ),
                ),
                (
                    "Treatment Machine(s)",
                    ", ".join(
                        set([str(beam.TreatmentMachineName) for beam in self._beams])
                    ),
                ),
            ]
        )
        dirty = self.plan_label
        sanitized = self.sanitized_plan_label
        if dirty != sanitized:
            info["Sanitized RT Plan Label"] = sanitized
        return info

    def __repr__(self):
        s = "\nPLAN\n\t" + "\n\t".join(
            ["{0:30s}: {1}".format(a, self.plan_info[a]) for a in self.plan_attrs]
        )
        s += "\nPATIENT\n\t" + "\n\t".join(
            ["{0:30s}: {1}".format(a, self.patient_info[a]) for a in self.patient_attrs]
        )
        s += "\nBEAMSET\n\t" + "\n\t".join(
            ["{0:30s}: {1}".format(a, self.bs_info[a]) for a in self.bs_attrs]
        )
        return s

class RT_structs:
    def __init__(self, dcm_dir, ss_ref_uid):
        # ss_ref_uid = self.rp_data.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
        print(
            "going to try to find the file with structure set with UID '{}'".format(
                ss_ref_uid
            )
        )
        nskip = 0
        ndcmfail = 0
        nwrongtype = 0
        rs_data = None
        rs_path = None
        for s in os.listdir(dcm_dir):
            if s[-4:].lower() != ".dcm":
                nskip += 1
                print("no .dcm suffix: {}".format(s))
                continue
            try:
                # print(s)
                ds = pydicom.dcmread(os.path.join(dcm_dir, s))
                dcmtype = ds.SOPClassUID.name
            except:
                ndcmfail += 1
                continue
            if (
                dcmtype == "RT Structure Set Storage"
                and ss_ref_uid == ds.SOPInstanceUID
            ):
                print("found structure set for CT: {}".format(s))
                rs_data = ds
                rs_path = os.path.join(dcm_dir, s)
                break
            else:
                nwrongtype += 1

        if rs_data is None:
            raise RuntimeError(
                "could not find structure set with UID={}; skipped {} with wrong suffix, got {} with 'dcm' suffix but pydicom could not read it, got {} with wrong class UID and/or instance UID. It could well be that this is a commissioning plan without CT and structure set data.".format(
                    ss_ref_uid, nskip, ndcmfail, nwrongtype
                )
            )
        check_RS(rs_data)
        self.structure_set = rs_data
        self.rs_path = rs_path
        self.roinumbers = []
        self.roinames = []
        self.roicontoursets = []
        self.roitypes = []

        # get ROIs
        self.get_ROIs()
        self.external = self.roinames[
            self.roitypes.index("EXTERNAL")
        ]  # TODO: what if none or more than one external ?

    def get_ROIs(self):
        for i, roi in enumerate(self.structure_set.StructureSetROISequence):
            try:
                # logger.debug("{}. ROI number {}".format(i,roi.ROINumber))
                # logger.debug("{}. ROI name   {}".format(i,roi.ROIName))
                roinumber = str(roi.ROINumber)  # NOTE: roi numbers are *strings*
                roiname = str(roi.ROIName)
                contourset = None
                roitype = None
                if i < len(self.structure_set.ROIContourSequence):
                    # normally this works
                    ci = self.structure_set.ROIContourSequence[i]
                    if str(ci.ReferencedROINumber) == roinumber:
                        contourset = ci
                if not contourset:
                    # logger.debug("(nr={},name={}) looks like this is a messed up structure set...".format(roinumber,roiname))
                    for ci in self.structure_set.ROIContourSequence:
                        if str(ci.ReferencedROINumber) == roinumber:
                            # logger.debug("(nr={},name={}) contour found, phew!".format(roinumber,roiname))
                            contourset = ci
                            break
                if not contourset:
                    pass
                    # logger.warn("ROI nr={} name={} does not have a contour, skipping it".format(roinumber,roiname))
                if i < len(self.structure_set.RTROIObservationsSequence):
                    # normally this works
                    obsi = self.structure_set.RTROIObservationsSequence[i]
                    if str(obsi.ReferencedROINumber) == roinumber:
                        roitype = str(obsi.RTROIInterpretedType)
                if not roitype:
                    # logger.debug("(nr={},name={}) looks like this is a messed up structure set...".format(roinumber,roiname))
                    for obsi in self.structure_set.RTROIObservationsSequence:
                        if str(obsi.ReferencedROINumber) == roinumber:
                            roitype = str(obsi.RTROIInterpretedType)
                            # logger.debug("(nr={},name={}) type={} found, phew!".format(roinumber,roiname,roitype))
                            break
                if not roitype:
                    pass
                    # logger.warn("ROI nr={} name={} does not have a type, skipping it".format(roinumber,roiname))
                if bool(roitype) and bool(contourset):
                    self.roinumbers.append(roinumber)
                    self.roinames.append(roiname)
                    self.roicontoursets.append(contourset)
                    self.roitypes.append(roitype)
            except Exception as e:
                raise RuntimeError(
                    "something went wrong with {}th ROI in the structure set: {}".format(
                        i, e
                    )
                )
                # logger.error("skipping that for now, keep fingers crossed")


def check_RS(dcm):
    data = dcm

    # keys and tags used by IDEAL from RS file
    genericTags = [
        "SOPClassUID",
        "SeriesInstanceUID",
        "StructureSetROISequence",
        "ROIContourSequence",
        "RTROIObservationsSequence",
        "ReferencedFrameOfReferenceSequence",
    ]
    structTags = ["ROIName", "ROINumber"]
    contourTags = ["ReferencedROINumber"]
    observTags = ["ReferencedROINumber", "RTROIInterpretedType"]

    ## --- Verify that all the tags are present and return an error if some are missing --- ##

    missing_keys = []

    # check first layer of the hierarchy
    loop_over_tags_level(genericTags, data, missing_keys)

    if "StructureSetROISequence" in data:
        # check structure set ROI sequence
        loop_over_tags_level(structTags, data.StructureSetROISequence[0], missing_keys)

    if "ROIContourSequence" in data:
        # check ROI contour sequence
        loop_over_tags_level(contourTags, data.ROIContourSequence[0], missing_keys)

    if "RTROIObservationsSequence" in data:
        # check ROI contour sequence
        loop_over_tags_level(
            observTags, data.RTROIObservationsSequence[0], missing_keys
        )

    if missing_keys:
        raise ImportError("DICOM RS file not conform. Missing keys: ", missing_keys)
    else:
        print("\033[92mRS file ok \033[0m")


def loop_over_tags_level(tags, data, missing_keys):
    for key in tags:
        if key not in data:
            missing_keys.append(key)
