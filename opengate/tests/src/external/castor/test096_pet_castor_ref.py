#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.pet.philipsvereos as vereos
import opengate.contrib.pet.castor_helpers as castor
from scipy.spatial.transform import Rotation
from test096_pet_castor_helpers import *
import os

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test096_pet_castor_interface"
    )

    # folders
    output_path = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    sec = gate.g4_units.s
    ns = gate.g4_units.ns
    ps = gate.g4_units.ps
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    MBq = 1e6 * Bq
    gcm3 = gate.g4_units.g_cm3
    deg = gate.g4_units.deg

    # options
    sim = gate.Simulation()
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = "auto"
    sim.number_of_threads = 4
    sim.output_dir = output_path
    # sim.progress_bar = True
    sim.verbose_level = gate.logger.NONE

    # world
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # create the pet and move it
    pet = vereos.add_pet(sim, "pet")
    pet.translation = [3 * cm, 4 * cm, 2 * cm]
    pet.rotation = Rotation.from_euler("yx", (20, 10), degrees=True).as_matrix()

    # get the crystal volume
    crystal = sim.volume_manager.get_volume("pet_crystal")
    die = sim.volume_manager.get_volume("pet_die")
    stack = sim.volume_manager.get_volume("pet_stack")
    module = sim.volume_manager.get_volume("pet_module")
    n_crystal = len(crystal.translation)
    n_die = len(die.translation)
    n_stack = len(stack.translation)
    n_module = len(module.translation)

    # set a (fake) digitizer
    hits_actor, blur_actor = add_test_digitizer(sim, crystal, "output_ref.root")
    blur_actor.use_truncated_Gaussian = True

    # source and physics
    stats = test_add_physics_and_stats(sim, "pet")
    activity = 1 * MBq / sim.number_of_threads
    if sim.visu:
        activity = 50 * Bq
    test_add_b2b_source(sim, activity)

    # Set the function that will create the file for castor.
    # This function is a hook because it must be run once the geometry is built by geant4.
    # The param structure contains input parameters and will contain the output castor_config
    # after the simulation
    filename = paths.output / "castor_config_ref.json"
    param = castor.set_hook_castor_config(sim, crystal.name, filename)

    # go
    duration = 1 * sec
    print(f"Run with {activity/Bq:.0f} Bq during {duration/sec:.03f} s")
    print(f"Mean time between events = {((1*sec)/(activity/Bq))/ns:.3f} ns")
    sim.run_timing_intervals = [[0, duration]]
    sim.run()

    # print info
    events = stats.counts.events
    print(f"Number of simulated events : {events}")

    # open the root file
    root_filename = hits_actor.get_output_path()
    root_file = uproot.open(root_filename)
    file_size = os.path.getsize(root_filename)
    print(f"Size of the file is {file_size / 1e6:.2f} MB")

    # consider the singles and hits trees
    hits_tree = root_file["hits"]
    n = int(hits_tree.num_entries)
    print(f"There are {n} hits")

    singles_tree = root_file["singles"]
    n = int(singles_tree.num_entries)
    print(f"There are {n} singles")

    # utility.test_ok(is_ok)
