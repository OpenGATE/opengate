from pathlib import Path
from opengate.utility import g4_units


def cc_digitizer(sim, Scatt, Abs, output_path):

    # Units
    keV = g4_units.keV
    MeV = g4_units.MeV
    mm = g4_units.mm
    ns = g4_units.ns

    # 1) Collect step-level hits

    hits_scatt = sim.add_actor("DigitizerHitsCollectionActor", "HitsScatt")
    hits_scatt.attached_to = Scatt.name
    hits_scatt.attributes = [
        "EventID",
        "TrackID",
        "TotalEnergyDeposit",
        "GlobalTime",
        "PrePosition",
        "PostPosition",
        "PreStepUniqueVolumeID",
    ]

    hits_abs = sim.add_actor("DigitizerHitsCollectionActor", "HitsAbs")
    hits_abs.attached_to = Abs.name
    hits_abs.attributes = hits_scatt.attributes
    scatt_collection = hits_scatt.name
    abs_collection = hits_abs.name

    # 2) Process Hits into Singles

    sing_scatt = sim.add_actor("DigitizerAdderActor", "SinglesScatt")
    sing_scatt.input_digi_collection = scatt_collection
    sing_scatt.policy = "EnergyWeightedCentroidPosition"
    sing_scatt.attributes = [
        "EventID",
        "GlobalTime",
        "TotalEnergyDeposit",
        "PostPosition",
    ]

    scatt_collection = sing_scatt.name

    sing_abs = sim.add_actor("DigitizerAdderActor", "SinglesAbs")
    sing_abs.input_digi_collection = abs_collection
    sing_abs.policy = "EnergyWeightedCentroidPosition"
    sing_abs.attributes = sing_scatt.attributes
    abs_collection = sing_abs.name

    # Spatial blurring

    spat_scatt = sim.add_actor("DigitizerSpatialBlurringActor", "SpatScatt")
    spat_scatt.attached_to = Scatt.name
    spat_scatt.input_digi_collection = scatt_collection
    spat_scatt.blur_attribute = "PostPosition"
    spat_scatt.blur_fwhm = [2 * mm, 2 * mm, 2 * mm]
    scatt_collection = spat_scatt.name

    spat_abs = sim.add_actor("DigitizerSpatialBlurringActor", "SpatAbs")
    spat_abs.attached_to = Abs.name
    spat_abs.input_digi_collection = abs_collection
    spat_abs.blur_attribute = "PostPosition"
    spat_abs.blur_fwhm = [2 * mm, 2 * mm, 2 * mm]
    abs_collection = spat_abs.name

    # Energy blurring

    reference_energy = 511 * keV
    scatt_resolution = 0.085  # FWHM/E at 511 keV
    abs_resolution = 0.125  # FWHM/E at 511 keV

    blur_scatt = sim.add_actor("DigitizerBlurringActor", "BlurScatt")
    blur_scatt.attached_to = Scatt.name
    blur_scatt.input_digi_collection = scatt_collection
    blur_scatt.blur_attribute = "TotalEnergyDeposit"
    blur_scatt.blur_method = "InverseSquare"
    blur_scatt.blur_reference_value = reference_energy
    blur_scatt.blur_resolution = scatt_resolution
    scatt_collection = blur_scatt.name

    blur_abs = sim.add_actor("DigitizerBlurringActor", "BlurAbs")
    blur_abs.attached_to = Abs.name
    blur_abs.input_digi_collection = abs_collection
    blur_abs.blur_attribute = "TotalEnergyDeposit"
    blur_abs.blur_method = "InverseSquare"
    blur_abs.blur_reference_value = reference_energy
    blur_abs.blur_resolution = abs_resolution
    abs_collection = blur_abs.name

    # Time blurring

    time_fwhm = 10 * ns
    time_sigma = time_fwhm / 2.355
    
    time_scatt = sim.add_actor("DigitizerBlurringActor", "TimeBlurScatt")
    time_scatt.attached_to = Scatt.name
    time_scatt.input_digi_collection = scatt_collection
    time_scatt.blur_attribute = "GlobalTime"
    time_scatt.blur_method = "Gaussian"
    time_scatt.blur_sigma = time_sigma
    scatt_collection = time_scatt.name

    time_abs = sim.add_actor("DigitizerBlurringActor", "TimeBlurAbs")
    time_abs.attached_to = Abs.name
    time_abs.input_digi_collection = abs_collection
    time_abs.blur_attribute = "GlobalTime"
    time_abs.blur_method = "Gaussian"
    time_abs.blur_sigma = time_sigma
    abs_collection = time_abs.name

    # Energy windows (thresholds)

    threshold_min = 70 * keV
    threshold_max = 2.0 * MeV

    thr_scatt = sim.add_actor("DigitizerEnergyWindowsActor", "ThrScatt")
    thr_scatt.attached_to = Scatt.name
    thr_scatt.input_digi_collection = scatt_collection
    thr_scatt.channels = [{"name": thr_scatt.name, "min": threshold_min, "max": threshold_max}]
    scatt_collection = thr_scatt.name

    thr_abs = sim.add_actor("DigitizerEnergyWindowsActor", "ThrAbs")
    thr_abs.attached_to = Abs.name
    thr_abs.input_digi_collection = abs_collection
    thr_abs.channels = [{"name": thr_abs.name, "min": threshold_min, "max": threshold_max}]

    #Saving root files to device (for later analysis)
    scatt_file = output_path / f"{thr_scatt.name}.root"
    abs_file   = output_path / f"{thr_abs.name}.root"

    thr_scatt.output_filename = str(scatt_file)
    thr_abs.output_filename   = str(abs_file)

    return scatt_file, abs_file
