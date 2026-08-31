#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test084")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.material = "G4_AIR"  # material used by default
    patient.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]

    # mu map actor (process at the first begin of run only)
    mumap = sim.add_actor("AttenuationImageActor", "mumap")
    mumap.image_volume = patient  # FIXME volume for the moment, not the name
    mumap.output_filename = "mumap.mhd"
    mumap.energy = 140.511 * keV
    mumap.database = "NIST"  # EPDL
    mumap.attenuation_image.write_to_disk = True
    mumap.attenuation_image.active = True
    print(f"Energy is {mumap.energy/keV} keV")
    print(f"Database is {mumap.database}")

    # go
    sim.run()

    # compare with ref
    ref = paths.output_ref / mumap.output_filename
    is_ok = utility.assert_images(
        ref,
        mumap.get_output_path(),
        tolerance=1e-4,
        fig_name=paths.output / "mumap1.png",
        sum_tolerance=1e-4,
    )

    utility.test_ok(is_ok)
