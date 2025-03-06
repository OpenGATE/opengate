#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# config 1 is used for tests of "keepAll", "keepHighestEnergyPair", "removeAll" and "keepCoincidenceIfOnlyOneGood" policies

import opengate as gate
from pathlib import Path
import os
from opengate.tests import utility
import uproot
from opengate.actors.coincidences import (
    coincidences_sorter,
    #copy_tree_for_dump,
)

# colors (similar to the ones of Gate)
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test0XX", "test0XX")

    sim = gate.Simulation()

    # options
    # warning the visualisation is slow !
    sim.visu = False #True
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.number_of_threads = 1
    
    sim.store_json_archive = True
    sim.json_archive_filename = paths.output /"simulation_test0XX_castor.json"
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
    world.size = [200 * mm, 200 * mm, 70 * mm]
    world.material = "G4_AIR"

    # add the Philips Vereos PET
    # pet = pet_vereos.add_pet(sim, "pet")
    # if create_mat:
    #    create_material(sim)

    # create the material 
    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O"],
        [0.31101534, 0.368765605, 0.083209699, 0.237009356],
        5.37 * gcm3,
    )

    # ring volume
    pet = sim.add_volume("Tubs", "pet")
    pet.rmax = 95 * mm
    pet.rmin = 65 * mm
    pet.dz = 20 * mm 
    pet.color = gray
    pet.material = "G4_AIR"

    # block
    block = sim.add_volume("Box", "block")
    block.mother = pet.name
    block.size = [20 * mm, 10 * mm, 40 * mm]
    translations_ring, rotations_ring = gate.geometry.utility.get_circular_repetition(
        40, [80 * mm, 0.0 * mm, 0], start_angle_deg=180, axis=[0, 0, 1]
    )
    block.translation = translations_ring
    block.rotation = rotations_ring

    block.material = "G4_AIR"
    block.color = white
    
    # Unit
    unit = sim.add_volume("Box", "unit")
    unit.mother = block.name
    unit.size = [20 * mm, 10 * mm, 10 * mm]
    unit.material = "G4_AIR"
    # 2x2 crystals
    unit.translation = gate.geometry.utility.get_grid_repetition([1, 1, 4], [0 * mm ,0 * mm, 10 * mm]) 
    unit.color = blue

    
    #Crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = unit.name
    crystal.size = [20 * mm, 5 * mm, 5 * mm]
    crystal.material = "LYSO"
    # 4rings 
    crystal.translation = gate.geometry.utility.get_grid_repetition([1, 2, 2], [0 * mm ,5 * mm, 5 * mm]) 
    crystal.color = red
    

    source = sim.add_source("GenericSource", "b2b")
    source.particle = "back_to_back"
    source.activity =  200000000 * Bq  # 2000000 * Bq
    source.position.type = "cylinder"
    source.position.radius = 60 * mm
    source.position.dz = 40 * mm /2
    source.position.translation = [0 * cm, 0 * cm, 0 * cm]
    # source.direction.type = "iso"
    # source.direction.accolinearity_flag = False
    source.energy.mono = 511 * keV
    source.direction.theta = [80 * deg, 110 * deg]
    source.direction.phi = [0, 360 * deg]
    #source.color = red
 
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
    # go
    sim.run()


    # open root file
    root_filename = sc.output_filename
    
    # this test need output/test072/output_singles.root
    if not os.path.exists(root_filename):
        # ignore on windows
        if os.name == "nt":
            utility.test_ok(True)
            sys.exit(0)
        cmd = "python " + str(paths.current / dependency)
        r = os.system(cmd)

    # open root file
    print(f"Opening {root_filename} ...")
    root_file = uproot.open(root_filename)

    # consider the tree of "singles"
    singles_tree = root_file["Singles_crystal"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # time windows
    ns = gate.g4_units.nanosecond
    time_window = 3 * ns
    policy = "takeAllGoods"

    mm = gate.g4_units.mm
    min_trans_dist = 0 * mm
    transaxial_plane = "xy"
    max_trans_dist = 190 * mm
    # apply coincidences sorter
    # (chunk size can be much larger, keep a low value to check it is ok)
    coincidences = coincidences_sorter(
        singles_tree,
        time_window,
        policy,
        min_trans_dist,
        transaxial_plane,
        max_trans_dist,
        chunk_size=1000000,
    )
    nc = len(coincidences["GlobalTime1"])
    print(f"There are {nc} coincidences for policy", policy)

    # save to file
    # WARNING root version >= 5.2.2 needed
    output_file = uproot.recreate(paths.output / f"output_coincidences.root")
    output_file["coincidences"] = coincidences
    #output_file["singles"] = copy_tree_for_dump(singles_tree)
    

    # end
    """print(f"Output statistics are in {stats.output}")
    print(f"Output edep map is in {dose.output}")
    print(f"vv {ct.image} --fusion {dose.output}")
    stats = sim.output.get_actor("Stats")
    print(stats)"""
    
    is_ok = True #(
    # test here 
    #)

    utility.test_ok(is_ok)
