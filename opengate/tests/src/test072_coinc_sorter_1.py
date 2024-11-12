#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    sim = gate.Simulation()

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    sec = gate.g4_units.s
    ps = gate.g4_units.ps
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3
    deg = gate.g4_units.deg

    # colors (similar to the ones of Gate)
    red = [1, 0, 0, 1]
    blue = [0, 0, 1, 1]
    green = [0, 1, 0, 1]
    yellow = [0.9, 0.9, 0.3, 1]
    gray = [0.5, 0.5, 0.5, 1]
    white = [1, 1, 1, 0.8]

    # folders
    paths = utility.get_default_test_paths(
        __file__, output_folder="test072_coinc_sorter"
    )

    # options
    # warning the visualisation is slow !
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.random_seed = 123456
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.store_json_archive = True
    sim.json_archive_filename = "simulation.json"

    # world
    sim.world.size = [450 * mm, 450 * mm, 70 * mm]
    sim.world.material = "G4_AIR"

    # create the materials
    sim.volume_manager.material_database.add_material_nb_atoms(
        "Lead", ["Pb"], [1], 11.4 * gcm3
    )
    sim.volume_manager.material_database.add_material_nb_atoms(
        "BGO", ["Bi", "Ge", "O"], [4, 3, 12], 7.13 * gcm3
    )

    sim.volume_manager.material_database.add_material_nb_atoms(
        "LSO", ["Lu", "Si", "O"], [2, 1, 5], 7.4 * gcm3
    )

    sim.volume_manager.material_database.add_material_weights(
        "LeadSb", ["Pb", "Sb"], [0.95, 0.05], 11.16 * gcm3
    )

    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O"],
        [0.31101534, 0.368765605, 0.083209699, 0.237009356],
        5.37 * gcm3,
    )

    # ring volume
    pet = sim.add_volume("Tubs", "pet")
    pet.rmax = 200 * mm
    pet.rmin = 127 * mm
    pet.dz = 32 * mm
    pet.color = gray
    pet.material = "G4_AIR"

    # block
    block = sim.add_volume("Box", "block")
    block.mother = pet
    block.size = [60 * mm, 10 * mm, 10 * mm]
    translations_ring, rotations_ring = gate.geometry.utility.get_circular_repetition(
        80, [160 * mm, 0.0 * mm, 0], start_angle_deg=180, axis=[0, 0, 1]
    )
    block.translation = translations_ring
    block.rotation = rotations_ring
    block.material = "G4_AIR"
    block.color = white

    # Crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = block
    crystal.size = [60 * mm, 10 * mm, 10 * mm]
    crystal.material = "LYSO"
    crystal.color = green

    # source
    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.activity = 20 * Bq
    source.position.type = "sphere"
    source.position.radius = 0.0000000000000005 * mm
    source.energy.mono = 511 * keV
    source.direction.theta = [90 * deg, 90 * deg]
    source.direction.phi = [0, 360 * deg]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal.name}")
    hc.attached_to = crystal
    hc.authorize_repeated_volumes = True
    hc.output_filename = "test72_output_1.root"
    hc.attributes = [
        "EventID",
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal.name}")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = hc.output_filename

    # timing
    sim.run_timing_intervals = [[0, 200 * sec]]

    # go
    sim.run()

    # end
    print(stats)

    # This test produces the data for the other 072_coinc_sorter tests
    stats_ref = paths.output_ref / "stats.txt"
    stats_ref = utility.read_stat_file(stats_ref)
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.04)

    utility.test_ok(is_ok)
