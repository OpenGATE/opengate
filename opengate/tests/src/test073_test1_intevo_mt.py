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
    sim.output_dir = paths.output

    # timing
    sim.random_seed = 123654789
    sec = gate.g4_units.second
    stop = 3 * sec
    if sim.visu:
        stop = 0.001 * sec
    sim.run_timing_intervals = [[0, stop]]

    # output filenames
    stats = sim.get_actor("stats")
    stats.output_filename = "stats1.txt"

    crystal = sim.volume_manager.get_volume(f"spect_crystal")
    proj = sim.get_actor(f"Projection_{crystal.name}")
    proj.output_filename = "projections_test1.mhd"

    hits = sim.get_actor(f"Hits_{crystal.name}")
    hits.output_filename = "output_test1.root"

    singles = sim.get_actor(f"Singles_{crystal.name}")
    singles.output_filename = "output_test1.root"

    # start simulation
    sim.run()

    # print stats
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
    is_ok = compare_stats(sim, paths.gate_output / "stats1.txt")

    # compare root
    fr = paths.gate_output / "output1.root"
    is_ok = compare_root_hits(crystal, sim, fr, paths.output) and is_ok

    # Compare root files
    sn = f"Singles_{crystal.name}"
    is_ok = compare_root_singles(crystal, sim, fr, paths.output, sn) and is_ok

    # compare images with Gate
    fr = paths.gate_output / "projection1.mhd"
    is_ok = compare_proj_images(crystal, sim, stats, fr, paths.output) and is_ok
    utility.test_ok(is_ok)
