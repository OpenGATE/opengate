#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.pet.philipsvereos as vereos
import opengate.contrib.pet.castor_helpers as castor
from scipy.spatial.transform import Rotation
from test096_pet_castor_helpers import *

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
    MBq = 1e6 * gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3
    deg = gate.g4_units.deg

    # options
    sim = gate.Simulation()
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = 123456
    sim.number_of_threads = 1
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
    hits_actor, blur_actor = add_test_digitizer(sim, crystal)
    blur_actor.keep_in_solid_limits = True
    blur_actor.use_truncated_Gaussian = False

    # source and physics
    stats = test_add_physics_and_stats(sim, "pet")
    activity = 1e3 * Bq / sim.number_of_threads
    if sim.visu:
        activity = 50 * Bq
    test_add_b2b_source(sim, activity)

    # Set the function that will create the file for castor.
    # This function is a hook because it must be run once the geometry is built by geant4.
    # The param structure contains input parameters and will contain the output castor_config
    # after the simulation
    filename = paths.output / "castor_config.json"
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
    print(f"Number of crystals : {n_crystal}")
    print(f"Number of dies     : {n_die}")
    print(f"Number of stacks   : {n_stack}")
    print(f"Number of modules  : {n_module}")
    total_crystals = n_crystal * n_die * n_stack * n_module

    # get the castor_config
    castor_config = param["castor_config"]
    n = len(castor_config["unique_volume_id"])
    is_ok = n == total_crystals
    utility.print_test(is_ok, f"The number of volumes is {n} vs {total_crystals}")

    """
        compare the hit's positions and the volume transformation in the castor file
    """

    # 1) read all hits/singles in the root file
    fn = hits_actor.get_output_path()
    print()
    is_ok = assert_positions(fn, "hits", castor_config, check_pos=True)
    print()
    # don't check the position for the singles as Position is replaced by weighted centroid
    is_ok = assert_positions(fn, "singles", castor_config) and is_ok
    print()
    # don't check the position for the singles as Position is replaced by blured position
    is_ok = assert_positions(fn, "singles_blur", castor_config) and is_ok

    utility.test_ok(is_ok)
