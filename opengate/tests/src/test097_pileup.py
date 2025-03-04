#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from pathlib import Path
from opengate.tests import utility
import uproot

green = [0, 1, 0, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test089", "test089")

    sim = gate.Simulation()

    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_seed = 1234
    sim.number_of_threads = 1

    # Units
    mm = gate.g4_units.mm
    sec = gate.g4_units.s
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3
    deg = gate.g4_units.deg

    # Folders
    data_path = paths.data
    output_path = paths.output

    # World
    world = sim.world
    world.size = [450 * mm, 450 * mm, 70 * mm]
    world.material = "G4_AIR"

    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O"],
        [0.31101534, 0.368765605, 0.083209699, 0.237009356],
        5.37 * gcm3,
    )

    # Ring volume
    pet = sim.add_volume("Tubs", "pet")
    pet.rmax = 200 * mm
    pet.rmin = 127 * mm
    pet.dz = 32 * mm
    pet.color = gray
    pet.material = "G4_AIR"

    # Block
    block = sim.add_volume("Box", "block")
    block.mother = pet.name
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
    crystal.mother = block.name
    crystal.size = [60 * mm, 10 * mm, 10 * mm]
    crystal.material = "LYSO"
    crystal.color = green

    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.activity = 200 * 1e6 * Bq
    source.position.type = "sphere"
    source.position.radius = 0.5 * 1e-15 * mm
    source.direction.theta = [90 * deg, 90 * deg]
    source.direction.phi = [0, 360 * deg]

    # Physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.root_output.write_to_disk = False
    hc.attributes = [
        "EventID",
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", "Singles_before_pileup")
    sc.attached_to = hc.attached_to
    sc.authorize_repeated_volumes = True
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = output_path / "output_singles.root"

    # Pile-up
    pu = sim.add_actor("DigitizerPileupActor", "Singles_after_pileup")
    pu.attached_to = hc.attached_to
    pu.authorize_repeated_volumes = True
    pu.input_digi_collection = sc.name
    pu.output_filename = sc.output_filename

    # Timing
    sim.run_timing_intervals = [[0, 0.002 * sec]]

    sim.run()

    print(stats)

    with uproot.open(sc.output_filename) as root_file:
        singles_tree = root_file["Singles_before_pileup"]
        pileup_tree = root_file["Singles_after_pileup"]

        print(f"{int(singles_tree.num_entries)} singles before")
        print(singles_tree.arrays(library="pd"))
        print(f"{int(pileup_tree.num_entries)} singles after pileup")
        print(pileup_tree.arrays(library="pd"))
