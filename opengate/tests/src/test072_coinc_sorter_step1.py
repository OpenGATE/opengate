#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# config 1 is used for tests of "keepAll", "keepHighestEnergyPair", "removeAll" and "keepCoincidenceIfOnlyOneGood" policies

import opengate as gate
from pathlib import Path
import os
from opengate.tests import utility

# colors (similar to the ones of Gate)
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test072", "test072")

    sim = gate.Simulation()

    # options
    # warning the visualisation is slow !
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.number_of_threads = 1

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

    # folders
    data_path = paths.data
    output_path = paths.output

    # world
    world = sim.world
    world.size = [450 * mm, 450 * mm, 70 * mm]
    world.material = "G4_AIR"

    # add the Philips Vereos PET
    # pet = pet_vereos.add_pet(sim, "pet")
    # if create_mat:
    #    create_material(sim)

    # create the material lead
    sim.volume_manager.material_database.add_material_nb_atoms(
        "Lead", ["Pb"], [1], 11.4 * gcm3
    )
    sim.volume_manager.material_database.add_material_nb_atoms(
        "Uranium", ["U"], [1], 18.9 * gcm3
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
    pet.dz = 32 * mm  # 340 * mm / 2.0
    pet.color = gray
    pet.material = "G4_AIR"

    # block
    block = sim.add_volume("Box", "block")
    block.mother = pet.name
    block.size = [60 * mm, 10 * mm, 10 * mm]
    # block.size = [1 * mm, 10 * mm, 10  * mm]
    # block.translation = [0 * mm, 324.3 * mm , 0 * mm]
    translations_ring, rotations_ring = gate.geometry.utility.get_circular_repetition(
        80, [160 * mm, 0.0 * mm, 0], start_angle_deg=180, axis=[0, 0, 1]
    )
    block.translation = translations_ring
    block.rotation = rotations_ring

    block.material = "G4_AIR"
    # block.translation = get_grid_repetition([1, 1, 4], [0, 0 * mm, 38.8 * mm])
    block.color = white

    # Crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = block.name
    # crystal.size = [1 * mm, 10 * mm, 10 * mm]
    # crystal.material = "Uranium"
    crystal.size = [60 * mm, 10 * mm, 10 * mm]
    crystal.material = "LYSO"
    # crystal.translation = gate.geometry.utility.get_grid_repetition([1, 1, 1], [3.9833 * mm ,0 * mm, 5.3 * mm])
    crystal.color = green

    """
    # If visu is enabled, we simplified the PET system, otherwise it is too slow
    if sim.visu:
        module = sim.volume_manager.get_volume("module")
        # only 2 repetition instead of 18
        translations_ring, rotations_ring = get_circular_repetition(
        72, [427 * mm, 0, 0], start_angle_deg=190, axis=[0, 0, 1]
        )
        module.translation = translations_ring
        module.rotation = rotations_ring
    """

    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.activity = 200000000 * Bq  # 2000000 * Bq
    # source.n = 1000
    source.position.type = "sphere"
    source.position.radius = 0.0000000000000005 * mm
    # source.direction.type = "iso"
    # source.direction.accolinearity_flag = False
    source.energy.mono = 511 * keV
    source.direction.theta = [90 * deg, 90 * deg]
    source.direction.phi = [0, 360 * deg]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    # sim.physics_manager.enable_decay = True
    # sim.physics_manager.set_production_cut("world", "all", 1 * m)
    # sim.physics_manager.set_production_cut("waterbox", "all", 1 * mm)

    # add the PET digitizer

    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal.name}")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    hc.output_filename = output_path / "output_singles.root"
    # hc.output = "output_config1.root"
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
    sim.run_timing_intervals = [[0, 0.0002 * sec]]
    # sim.run_timing_intervals = [[0, 0.01 * sec]]
    # go
    sim.run()

    # end
    """print(f"Output statistics are in {stats.output}")
    print(f"Output edep map is in {dose.output}")
    print(f"vv {ct.image} --fusion {dose.output}")
    stats = sim.output.get_actor("Stats")
    print(stats)"""
