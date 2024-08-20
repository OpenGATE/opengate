#!/usr/bin/env python3
# -----------------------------------------------------------------------------
#   Copyright (C): MedAustron GmbH, ACMIT Gmbh and Medical University Vienna
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE for further details
# -----------------------------------------------------------------------------

import pydicom
import os
import re
import numpy as np
import logging
from scipy.spatial.transform import Rotation
import opengate as gate

logger = logging.getLogger(__name__)


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

    beam_data = dict()
    beam_data["n_fields"] = 0
    beam_data["plan_name"] = ""
    beam_data["msw_beam"] = 0
    beam_data["energies"] = []
    beam_data["nb_spots"] = []
    beam_data["spots"] = []
    beam_data["gantry_angle"] = 0
    beam_data["couch_angle"] = 0
    beam_data["isocenter"] = []
    found_field = False
    start_index = []

    # read  content
    with open(txtFile, "r") as f:
        lines = f.readlines()

    # get plan's info
    # TODO: make function to check line tag
    for i, line in enumerate(lines):
        if check_plan_tag(line, "PlanName"):
            l = lines[i + 1].split("\n")[0]
            beam_data["plan_name"] = l
        if check_plan_tag(line, "NumberOfFields"):
            l = lines[i + 1].split("\n")[0]
            beam_data["n_fields"] = int(l)
            if beam_nr > beam_data["n_fields"]:

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
                beam_data["gantry_angle"] = float(l)
            if check_plan_tag(line, "PatientSupportAngle"):
                l = lines[i + 1].split("\n")[0]
                beam_data["couch_angle"] = float(l)
            if check_plan_tag(line, "IsocenterPosition"):
                l = lines[i + 1].split("\n")[0]
                beam_data["isocenter"] = [float(i) for i in l.split()]
            if check_plan_tag(line, "FinalCumulativeMeterSetWeight"):
                l = lines[i + 1].split("\n")[0]
                beam_data["msw_beam"] = float(l)
            if check_plan_tag(line, "Energy"):
                l = lines[i + 1].split("\n")[0]
                beam_data["energies"].append(float(l))
            if check_plan_tag(line, "NbOfScannedSpots"):
                l = lines[i + 1].split("\n")[0]
                beam_data["nb_spots"].append(int(l))
            if check_plan_tag(line, "X Y Weight"):
                start_index.append(i + 1)

    for i in range(len(beam_data["energies"])):
        e = beam_data["energies"][i]
        # print(f"ENERGY: {e}")
        start = start_index[i]
        end = start_index[i] + beam_data["nb_spots"][i]
        for j in range(start, end):
            l = lines[j].split("\n")[0].split()
            spot = SpotInfo(float(l[0]), float(l[1]), float(l[2]), e)
            spot.beamFraction = float(l[2]) / beam_data["msw_beam"]
            spot.particle_name = ionType
            beam_data["spots"].append(spot)

    return beam_data


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
    beam = beamset.beams[beam_nr - 1]
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
        self._rp = pydicom.read_file(rpfp)
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
                    (
                        "NA"
                        if not hasattr(self._rp, a.replace(" ", ""))
                        else str(getattr(self._rp, a.replace(" ", "")))
                    ),
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


class TreatmentPlanSource:
    def __init__(self, name, sim):
        self.name = name
        # self.mother = None
        self.rotation = Rotation.identity()
        self.translation = [0, 0, 0]
        self.spots = None
        self.beamline_model = None
        self.n_sim = 0
        self.sim = sim  # simulation obj to which we want to add the tp source

    def set_particles_to_simulate(self, n_sim):
        self.n_sim = n_sim

    def set_spots(self, spots):
        self.spots = spots

    def set_spots_from_rtplan(self, rt_plan_path, beam_nr=1):
        beamset = BeamsetInfo(rt_plan_path)
        gantry_angle = beamset.beam_angles[beam_nr - 1]
        spots = get_spots_from_beamset_beam(beamset, beam_nr)
        self.spots = spots
        self.rotation = Rotation.from_euler("z", gantry_angle, degrees=True)

    def set_beamline_model(self, beamline):
        self.beamline_model = beamline

    def initialize_tpsource(self, flat_generation=False, activity=False):
        # some alias
        Bq = gate.g4_units.Bq
        spots_array = self.spots
        sim = self.sim
        nSim = self.n_sim
        beamline = self.beamline_model
        self.d_nozzle_to_iso = beamline.distance_nozzle_iso
        self.d_stearMag_to_iso_x = beamline.distance_stearmag_to_isocenter_x
        self.d_stearMag_to_iso_y = beamline.distance_stearmag_to_isocenter_y

        # mapping factors between iso center plane and nozzle plane (due to steering magnets)
        cal_proportion_factor = lambda d_magnet_iso: (
            1
            if (d_magnet_iso == float("inf"))
            else (d_magnet_iso - self.d_nozzle_to_iso) / d_magnet_iso
        )
        self.proportion_factor_x = cal_proportion_factor(self.d_stearMag_to_iso_x)
        self.proportion_factor_y = cal_proportion_factor(self.d_stearMag_to_iso_y)
        tot_sim_particles = 0

        n_part_spots_V = self._sample_n_particles_spots(flat_generation=flat_generation)

        # initialize a pencil beam for each spot
        for i, spot in enumerate(spots_array):
            # if flat_generation:
            #     # simualte same number of particles for each spot
            #     nspot = nSim / len(spots_array)
            # else:
            #     # simulate a fraction of the beam particles for this spot
            #     nspot = spot.beamFraction * nSim

            nspot = n_part_spots_V[i]
            if nspot == 0:
                continue

            source = sim.add_source("IonPencilBeamSource", f"{self.name}_spot_{i}")

            # set energy
            source.energy.type = "gauss"
            source.energy.mono = beamline.get_energy(nominal_energy=spot.energy)
            source.energy.sigma_gauss = beamline.get_sigma_energy(
                nominal_energy=spot.energy
            )

            source.particle = spot.particle_name
            source.position.type = "disc"  # pos = Beam, shape = circle + sigma

            # # set mother
            # if self.mother is not None:
            #     source.mother = self.mother

            # POSITION:
            source.position.translation = self._get_pbs_position(spot)

            # ROTATION:
            source.position.rotation = self._get_pbs_rotation(spot)

            # add weight
            if flat_generation:
                source.weight = spot.beamFraction * len(spots_array)
                print(f"{source.weight = }")

            # set number of particles
            if activity:
                source.activity = nspot * Bq
            else:
                # nspot = np.round(nspot)
                source.n = nspot

            tot_sim_particles += nspot

            # set optics parameters
            source.direction.partPhSp_x = [
                beamline.get_sigma_x(spot.energy),
                beamline.get_theta_x(spot.energy),
                beamline.get_epsilon_x(spot.energy),
                beamline.conv_x,
            ]
            source.direction.partPhSp_y = [
                beamline.get_sigma_y(spot.energy),
                beamline.get_theta_y(spot.energy),
                beamline.get_epsilon_y(spot.energy),
                beamline.conv_y,
            ]

        self.actual_sim_particles = tot_sim_particles

    def _sample_n_particles_spots(self, flat_generation=False):
        if flat_generation:
            pdf = [1 / len(self.spots) for spot in self.spots]
        else:
            pdf = [spot.beamFraction for spot in self.spots]

        # normalize vector, to assure the probabilities sum up to 1
        pdf = pdf / np.sum(pdf)

        n_spots = len(self.spots)
        n_part_spots_V = np.zeros(n_spots)
        for i in range(int(self.n_sim)):
            bin = np.random.choice(np.arange(0, n_spots), p=pdf)
            n_part_spots_V[bin] += 1

        return n_part_spots_V

    def _get_pbs_position(self, spot):
        # (x,y) referr to isocenter plane.
        # Need to be corrected to referr to nozzle plane
        pos = [
            (spot.xiec) * self.proportion_factor_x,
            (spot.yiec) * self.proportion_factor_y,
            self.d_nozzle_to_iso,
        ]
        # Gantry angle = 0 -> source comes from +y and is positioned along negative side of y-axis
        # https://opengate.readthedocs.io/en/latest/source_and_particle_management.html

        position = (self.rotation * Rotation.from_euler("x", np.pi / 2)).apply(
            pos
        ) + self.translation

        return position

    def _get_pbs_rotation(self, spot):
        # by default the source points in direction z+.
        # Need to account for SM direction deviation and rotation thoward isocenter (270 deg around x)
        # then rotate of gantry angle
        rotation = [0.0, 0.0, 0.0]
        beta = np.arctan(spot.yiec / self.d_stearMag_to_iso_y)
        alpha = np.arctan(spot.xiec / self.d_stearMag_to_iso_x)
        rotation[0] = -np.pi / 2 + beta
        rotation[2] = -alpha

        # apply gantry angle
        spot_rotation = (
            self.rotation * Rotation.from_euler("xyz", rotation)
        ).as_matrix()

        return spot_rotation
