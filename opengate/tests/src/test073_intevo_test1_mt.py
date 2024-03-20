#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test073_helpers import *
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="gate_test073_intevo", output_folder="test073"
    )

    # create the simulation
    sim = gate.Simulation()
    create_sim_tests(sim, threads=4, digitizer=1)

    # timing
    sim.random_seed = 123654789
    sec = gate.g4_units.second
    stop = 3 * sec
    if sim.visu:
        stop = 0.001 * sec
    sim.run_timing_intervals = [[0, stop]]

    # output filenames
    stats = sim.get_actor_user_info("stats")
    stats.output = paths.output / "stats1.txt"
    crystal = sim.volume_manager.get_volume(f"spect_crystal")
    proj = sim.get_actor_user_info(f"Projection_{crystal.name}")
    proj.output = paths.output / "projections_test1.mhd"
    hits = sim.get_actor_user_info(f"Hits_{crystal.name}")
    hits.output = paths.output / "output_test1.root"
    singles = sim.get_actor_user_info(f"Singles_{crystal.name}")
    singles.output = paths.output / "output_test1.root"

    # start simulation
    sim.run()

    # print stats
    output = sim.output
    stats = output.get_actor("stats")
    print(stats)

    # ------------------------------------------------------------------------------------
    # FIXME: WARNING !!!!
    # This is ** not ** a validation of the SPECT model.
    # This is a FAKE digitizer.
    # This test only checks that the output is consistant with some reference data obtained
    # with an old Gate9 simulation.
    # This test will change in the future, once the validation is completed.
    # FIXME: WARNING !!!!
    # ------------------------------------------------------------------------------------

    # compare stats
    is_ok = compare_stats(output, paths.gate_output / "stats1.txt")

    # compare root
    fr = paths.gate_output / "output1.root"
    is_ok = compare_root_hits(crystal, output, fr, paths.output) and is_ok

    # Compare root files
    stats = output.get_actor("stats")
    sn = f"Singles_{crystal.name}"
    is_ok = compare_root_singles(crystal, output, fr, paths.output, sn) and is_ok

    # compare images with Gate
    fr = paths.gate_output / "projection1.mhd"
    is_ok = compare_proj_images(crystal, output, stats, fr, paths.output) and is_ok
    utility.test_ok(is_ok)
