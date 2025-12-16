#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.sources.utility import get_spectrum


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
    gcm3 = gate.g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.material = "G4_AIR"  # material used by default
    f1 = str(paths.data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.data / "Schneider2000DensitiesTable.txt")
    tol = 0.01 * gcm3
    print(f"HU density tolerance: {tol/gcm3} gcm3")
    patient.voxel_materials, materials = (
        gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    )
    print(f"Number of materials: {len(materials)}")

    # mu map actor (process at the first "begin of run" only)
    mumap = sim.add_actor("AttenuationImageActor", "mumap")
    mumap.image_volume = patient  # FIXME volume for the moment, not the name
    mumap.output_filename = "mumap2.mhd"
    energies = get_spectrum("Lu177", "gamma", "radar").energies
    mumap.energy = energies[3]  # 0.208 keV
    mumap.database = "EPDL"  # NIST or EPDL
    print(f"Energy is {mumap.energy/keV} keV")
    print(f"Database is {mumap.database}")

    # remove verbose
    sim.verbose_level = "NONE"
    sim.run(start_new_process=True)

    # compare with ref
    ref = paths.output_ref / mumap.output_filename
    is_ok = utility.assert_images(
        ref,
        mumap.get_output_path(),
        tolerance=1e-5,
        fig_name=paths.output / "mumap2.png",
        sum_tolerance=1e-5,
    )

    utility.test_ok(is_ok)
