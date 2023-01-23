### ------------------------------------------------------------------------------------------------- ##
#  Re-elaboration from: https://github.com/OpenGATE/GateTools/blob/master/gatetools/pbs_plan_file.py
### ------------------------------------------------------------------------------------------------- ###

import pydicom
import numpy as np


class Spot:
    def __init__(self, xiec, yiec, w):
        self.x = xiec
        self.y = yiec
        self.w = w
        self.t0 = None
        self.t1 = None


class Layer:
    def __init__(self, icp_id, E, n_spots, xV, yV, wV, msw):
        self.tuneID = icp_id
        self.energy = E
        self.x = xV
        self.y = yV
        self.w = wV
        self.msw = msw
        self.nspots = n_spots

    @property
    def spots(self):
        return [Spot(x, y, w) for (x, y, w) in zip(self.x, self.y, self.w)]


class Beam:
    def __init__(self, beamnr, iso_C, g_angle, p_angle, mswtot):
        self.beamNr = beamnr
        self.isoCenter = iso_C
        self.gantry_angle = g_angle
        self.patient_angle = p_angle
        self.mswtot = mswtot
        self.layers = None

    def set_energy_layers(self, control_points_list):
        self.layers = control_points_list


def dicom_rt_pbs_plan_to_object(
    dcm_input, dcm_checks=False, allow0=False, verbose=False
):

    all_beams = []
    nspots_ignored = 0
    nlayers_ignored = 0
    rp, mswtots, beamnrs, iso_Cs, g_angles, p_angles = _read_and_check_dicom_plan_file(
        dcm_input, dcm_checks, verbose
    )

    # stupidity check...
    assert len(rp.IonBeamSequence) == len(beamnrs)
    assert len(rp.IonBeamSequence) == len(mswtots)
    assert len(rp.IonBeamSequence) == len(iso_Cs)
    assert len(rp.IonBeamSequence) == len(g_angles)
    assert len(rp.IonBeamSequence) == len(p_angles)
    # loop over beams
    for ion_beam, beamnr, mswtot, iso_C, g_angle, p_angle in zip(
        rp.IonBeamSequence, beamnrs, mswtots, iso_Cs, g_angles, p_angles
    ):
        newBeamObj = Beam(beamnr, iso_C, g_angle, p_angle, mswtot)
        nspots_list = list()
        mask_list = list()
        weights_list = list()
        # loop over energy layers
        for icp in ion_beam.IonControlPointSequence:
            nspots_nominal = int(icp.NumberOfScanSpotPositions)
            if nspots_nominal == 1:
                w_all = np.array([float(icp.ScanSpotMetersetWeights)])
            else:
                w_all = np.array([float(w) for w in icp.ScanSpotMetersetWeights])
            # valid spots positions
            mask = (w_all >= 0.0) if allow0 else (w_all > 0.0)
            mask_list.append(mask)
            # number of valid spots
            nspots_list.append(np.sum(mask))
            # weights array
            weights_list.append(w_all)

        msw_cumsum = 0.0
        cpi = 0
        control_points_list = []
        # loop again over energy layer
        for icp, nspots, mask, w_all in zip(
            ion_beam.IonControlPointSequence, nspots_list, mask_list, weights_list
        ):
            nspots_nominal = int(icp.NumberOfScanSpotPositions)
            if nspots == 0:
                if allow0:
                    print(
                        "this should not happen, nspots_nominal={}",
                        format(nspots_nominal),
                    )
                nlayers_ignored += 1
                nspots_ignored += nspots_nominal
                continue
            # get in plane spot positions
            xy = np.array([float(pos) for pos in icp.ScanSpotPositionMap]).reshape(
                nspots_nominal, 2
            )
            nspots_ignored += nspots_nominal - nspots
            w = w_all[mask]
            x = xy[mask, 0]
            y = xy[mask, 1]
            msw = np.sum(w_all[mask])
            energy = float(icp.NominalBeamEnergy)
            # Maybe we should emit noisy warnings if the tune ID is missing?
            tuneID = "0.0" if not "ScanSpotTuneID" in icp else str(icp.ScanSpotTuneID)
            # TODO: what if all spot weights in this ICP are zero?
            control_point = Layer(icp.ControlPointIndex, energy, nspots, x, y, w, msw)
            control_points_list.append(control_point)

        newBeamObj.set_energy_layers(control_points_list)
        all_beams.append(newBeamObj)

    return all_beams


def _check_rp_dicom_file(rp_filepath, dcm_checks=False, verbose=False):
    """
    Auxiliary implementation function.
    Try to read the DICOM file and perform some paranoid check of the essential DICOM attributes.
    """
    # if the input file path is not readable as a DICOM file, then pydicom will throw an appropriate exception
    rp = pydicom.dcmread(rp_filepath)
    if dcm_checks:
        for attr in ["SOPClassUID", "IonBeamSequence"]:
            if attr not in rp:
                raise IOError(
                    "bad DICOM file {},\nmissing '{}'".format(rp_filepath, attr)
                )
        if rp.SOPClassUID.name != "RT Ion Plan Storage":
            raise IOError(
                "bad plan file {},\nwrong SOPClassUID: {}='{}',\nexpecting an 'RT Ion Plan Storage' file instead.".format(
                    rp_filepath, rp.SOPClassUID, rp.SOPClassUID.name
                )
            )
        n_ion_beams = len(rp.IonBeamSequence)
        ion_beams = rp.IonBeamSequence
        for ion_beam in ion_beams:
            for attr in ["BeamNumber", "IonControlPointSequence"]:
                if attr not in ion_beam:
                    raise IOError(
                        "bad DICOM file {},\nmissing '{}' in ion beam".format(
                            rp_filepath, attr
                        )
                    )
            for cpi, icp in enumerate(ion_beam.IonControlPointSequence):
                for attr in [
                    "NumberOfScanSpotPositions",
                    "ScanSpotPositionMap",
                    "ScanSpotMetersetWeights",
                ]:
                    if attr not in icp:
                        raise IOError(
                            "bad DICOM file {},\nmissing '{}' in {}th ion control point".format(
                                rp_filepath, attr, cpi
                            )
                        )
        if verbose:
            print("Input DICOM file seems to be a legit 'RT Ion Plan Storage' file.")
    return rp


def _get_beam_numbers(rp, verbose=False):
    """
    Auxiliary implementation function.
    Extract beam numbers from the DICOM plan dataset, and create better ones in
    case the stored ones are useless for some reason.
    Most treatment planning systems will assign a non-negative unique beam
    number to each ion beam, but some TPS (ones used to generate artificial
    plans for testing and commissioning purposes) are negligent in that regard.
    Since Gate needs the beam numbers in order to allow the user to select
    which beams to simulate (or conversely, which beams to ignore), this script
    will create fake but usable beam numbers in such cases.
    """
    number_list = list()
    input_beam_numbers_are_ok = True
    n_ion_beams = len(rp.IonBeamSequence)
    for ion_beam in rp.IonBeamSequence:
        if input_beam_numbers_are_ok:
            nr = int(ion_beam.BeamNumber)
            if nr < 0:
                input_beam_numbers_are_ok = False
                if verbose:
                    print("CORRUPT INPUT: found a negative beam number {}.".format(nr))
            elif nr in number_list:
                input_beam_numbers_are_ok = False
                if verbose:
                    print(
                        "CORRUPT INPUT: found same beam number {} for multiple beams.".format(
                            nr
                        )
                    )
            else:
                # still good, keep fingers crossed...
                number_list.append(nr)
    if not input_beam_numbers_are_ok:
        if verbose:
            print(
                "will use simple enumeration of beams instead of the (apparently corrupt) dicom beam numbers."
            )
        number_list = np.arange(1, n_ion_beams + 1).tolist()
    return number_list


def _get_mswtot_list(rp, verbose=False):
    """
    Auxiliary implementation function.
    Retrieve the total weight of all spots for one "control point" (or "layer",
    or "energy").  TODO: it could be useful to enable a conversion function
    here, e.g. to convert from "monitor units" to "number of protons". However,
    this can also be taken care of in Gate itself, via the beam calibration
    polynomial in the "source properties file".
    """
    mswtot_list = list()
    for ion_beam in rp.IonBeamSequence:
        mswtot = 0.0
        for icp in ion_beam.IonControlPointSequence:
            nspot = int(icp.NumberOfScanSpotPositions)
            if nspot == 1:
                mswtot += float(icp.ScanSpotMetersetWeights)
            else:
                # Weights should be non-negative, but let's be paranoid.
                mswtot += np.sum(
                    np.array([float(w) for w in icp.ScanSpotMetersetWeights if w > 0.0])
                )
        mswtot_list.append(mswtot)
        # print(f'{mswtot=}')
        # print(f'mswtot rtp={ion_beam.FinalCumulativeMetersetWeight}')

    return mswtot_list


def _get_angles_and_isoCs(rp, verbose):
    """
    Auxiliary implementation function.
    For each beam, retrieve the gantry angle, patient support angle and
    isocenter, if available.  (Most TPS will of course specify this info, but
    some medical physicists use an in-house TPS for generating special plans
    for beam verification and commissioning, with incomplete planning
    information.) For some unclear reasons, the angles and isocenter
    coordinates are not stored as attributes of the ion beam, but rather as
    attributes to the first "ion control point".
    """
    gantry_angle_list = list()
    patient_angle_list = list()
    iso_center_list = list()
    n_ion_beams = len(rp.IonBeamSequence)
    dubious = False
    for i, ion_beam in enumerate(rp.IonBeamSequence):
        # each of these quantities may be missing
        beamname = (
            str(i) if not hasattr(ion_beam, "BeamName") else str(ion_beam.BeamName)
        )
        icp0 = ion_beam.IonControlPointSequence[0]
        # check isocenter
        if "IsocenterPosition" in icp0 and icp0.IsocenterPosition is not None:
            if len(icp0.IsocenterPosition) == 3:
                iso_center_list.append(
                    np.array([float(icp0.IsocenterPosition[j]) for j in range(3)])
                )
        else:
            print(
                "absent/corrupted isocenter for beam '{}'; assuming [0,0,0] for now, please fix this manually.".format(
                    beamname
                )
            )
            iso_center_list.append(np.zeros(3, dtype=float))
            dubious = True
        # check gantry angle
        if "GantryAngle" in icp0 and icp0.GantryAngle is not None:
            gantry_angle_list.append(float(icp0.GantryAngle))
        else:
            print(
                "no gantry angle specified for beam '{}' in treatment plan; assuming 0. for now, please fix this manually.".format(
                    beamname
                )
            )
            gantry_angle_list.append(0.0)
            dubious = True
        # check couch angle
        if "PatientSupportAngle" in icp0 and icp0.PatientSupportAngle is not None:
            patient_angle_list.append(float(icp0.PatientSupportAngle))
        else:
            print(
                "no patient support angle specified for beam '{}' in treatment plan; assuming 0. for now, please fix this manually.".format(
                    beamname
                )
            )
            patient_angle_list.append(0.0)
            dubious = True
    if verbose and not dubious:
        print("patient/gantry angles and isocenters all seem fine.")
    return gantry_angle_list, patient_angle_list, iso_center_list


def _read_and_check_dicom_plan_file(rp_filepath, dcm_checks=False, verbose=False):
    """
    Auxiliary implementation function.
    The existence of a DICOM 'standard' does not mean that all 'DICOM plan
    files' look alike, unfortunately; every TPS has its own dialect, and some medical
    physicists use their own hobby TPS to create "DICOM plan files" that are lacking
    the most basic ingredients. We need to check our assumptions based on the
    TPS plan files that we have had access to, and define workarounds for the
    problematic "plan files".
    """
    # Crude checks of DICOM file structure.
    rp = _check_rp_dicom_file(rp_filepath, dcm_checks, verbose)
    # Get mswtot of each beam.
    mswtot_list = _get_mswtot_list(rp, verbose)
    # Get 'number' of each beam.
    # (Name would more more useful, but Gate uses the number in its interface for "allowing" and "disallowing" beams ("fields").)
    number_list = _get_beam_numbers(rp, verbose)
    # Get the things that *should* be attributes of an "ion beam" object but which are buried in "control point number 0".
    gantry_angles, patient_angles, isoCs = _get_angles_and_isoCs(rp, verbose)

    return rp, mswtot_list, number_list, isoCs, gantry_angles, patient_angles
