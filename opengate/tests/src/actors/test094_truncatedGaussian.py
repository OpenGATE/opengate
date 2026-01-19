#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import uproot

# Create the simulation
import numpy as np
from opengate.tests import utility


def check_stats(path, fwhmX, fwhmY, fwhmZ):

    is_ok = True

    inFile = uproot.open(path)
    Singles_TG = inFile["Singles_crystal"]
    Singles_SB_TG = inFile["Singles_crystal_2"]

    # Convert branches to numpy arrays (fast and efficient)
    X_TG = Singles_TG["PostPosition_X"]
    Y_TG = Singles_TG["PostPosition_Y"]
    Z_TG = Singles_TG["PostPosition_Z"]

    X_SB_TG = Singles_SB_TG["PostPosition_X"]
    Y_SB_TG = Singles_SB_TG["PostPosition_Y"]
    Z_SB_TG = Singles_SB_TG["PostPosition_Z"]

    dX = np.asarray(X_TG) - np.asarray(X_SB_TG)
    dY = np.asarray(Y_TG) - np.asarray(Y_SB_TG)
    dZ = np.asarray(Z_TG) - np.asarray(Z_SB_TG)

    if (np.abs(np.std(dX) * 2.35 - fwhmX) / fwhmX) > 0.05:
        print("ERROR IN X!")
        is_ok = False

    if (np.abs(np.std(dY) * 2.35 - fwhmY) / fwhmY) > 0.05:
        print("ERROR IN Y!")
        is_ok = False

    if (np.abs(np.std(dZ) * 2.35 - fwhmZ) / fwhmZ) > 0.05:
        print("ERROR IN Z!")
        is_ok = False

    return is_ok


def main():
    paths = utility.get_default_test_paths(__file__, "", output_folder="test060")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.check_volumes_overlap = True
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    output_path = paths.output
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    KeV = gate.g4_units.keV
    kBq = gate.g4_units.Bq * 1000
    gcm3 = gate.g4_units.g_cm3
    sec = gate.g4_units.s

    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O"],
        [0.31101534, 0.368765605, 0.083209699, 0.237009356],
        5.37 * gcm3,
    )

    ###Test for GATE10 truncated Gaussian###

    # world
    world = sim.world
    world.size = [100 * cm, 100 * cm, 100 * cm]
    world.material = "G4_AIR"

    crystal = sim.add_volume("Box", name="crystal")
    crystal.size = [10 * cm, 10 * cm, 10 * cm]
    crystal.material = "LYSO"
    crystal.mother = world.name

    source = sim.add_source("GenericSource", "mysource")
    source.particle = "gamma"

    source.position.type = "box"
    source.position.size = [crystal.size[0] * 0.99, crystal.size[1] * 0.99, 0.1 * mm]
    source.position.translation = [0 * cm, 0 * cm, -5 * cm]

    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.energy.type = "mono"
    source.energy.mono = 511 * KeV
    source.activity = 20 * kBq

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal.name}")
    hc.attached_to = crystal.name
    hc.output_filename = output_path / "output_singles_TEST.root"
    # hc.output = "output_config1.root"
    hc.attributes = [
        "EventID",
        "PostPosition",
        "PrePosition",
        "Position",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "PostStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal.name}")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output_filename = hc.output_filename

    bc = sim.add_actor("DigitizerSpatialBlurringActor", f"Singles_{crystal.name}_2")
    bc.attached_to = hc.attached_to
    bc.output_filename = hc.output_filename
    bc.input_digi_collection = sc.name
    bc.keep_in_solid_limits = True
    bc.use_truncated_Gaussian = True
    bc.blur_attribute = "PostPosition"
    bc.blur_fwhm = [35 * mm, 20 * mm, 1 * mm]

    # timing
    sim.run_timing_intervals = [[0, 1 * sec]]
    # sim.run_timing_intervals = [[0, 0.01 * sec]]
    # go
    sim.run()

    is_ok = check_stats(hc.output_filename, *bc.blur_fwhm)
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
