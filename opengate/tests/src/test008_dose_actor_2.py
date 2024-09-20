#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test008")

    # create the simulation
    sim = gate.Simulation()

    # options
    sim.visu = False
    sim.visu_type = "vrml"
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.random_seed = 42321

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g / cm3

    # world
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_AIR"

    # pat
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    print(f"Reading image {patient.image}")
    patient.material = "G4_AIR"  # material used by default
    patient.translation = [0, 0, 272 * mm]
    f1 = paths.data / "Schneider2000MaterialsTable.txt"
    f2 = paths.data / "Schneider2000DensitiesTable.txt"
    tol = 0.1 * gcm3
    (
        patient.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    print(f"tol = {tol/gcm3} g/cm3")
    print(f"mat : {len(patient.voxel_materials)} materials")

    # physics (opt1 is faster than opt4, but less accurate)
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option1"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)
    sim.physics_manager.set_production_cut("patient", "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "mysource")
    source.particle = "proton"
    source.energy.mono = 150 * MeV
    source.position.type = "disc"
    source.position.radius = 3 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "stats.txt"

    # dose actor 1: depth edep
    doseactor = sim.add_actor("DoseActor", "depth")
    doseactor.attached_to = "patient"
    doseactor.output_filename = "depth.mhd"
    doseactor.spacing = [5 * mm, 5 * mm, 5 * mm]
    doseactor.size = [50, 50, 50]
    doseactor.output_coordinate_system = "attached_to_image"
    doseactor.dose.active = True
    doseactor.dose_uncertainty.active = True
    doseactor.density.active = True

    # run
    sim.run()

    # print stat
    print(stats)

    is_ok = True
    print("\nDifference for EDEP")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "depth_dose.mhd",
            doseactor.dose.get_output_path(),
            stats,
            tolerance=25,
            ignore_value=0,
            sum_tolerance=1,
        )
        and is_ok
    )

    print("\nDifference for uncertainty")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "depth_dose_uncertainty.mhd",
            doseactor.dose_uncertainty.get_output_path(),
            stats,
            tolerance=5,
            ignore_value=1,
            sum_tolerance=1,
        )
        and is_ok
    )

    """print("\nDifference for density")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "depth_density.mhd",
            doseactor.density.get_output_path(),
            stats,
            tolerance=5,
            ignore_value=1,
            sum_tolerance=1,
        )
        and is_ok
    )"""

    utility.test_ok(is_ok)
