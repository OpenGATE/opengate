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
    create_sim_tests(sim, threads=4, digitizer=2)

    # timing
    sim.random_seed = 123654789
    sec = gate.g4_units.second
    stop = 3 * sec
    if sim.visu:
        stop = 0.001 * sec
    sim.run_timing_intervals = [[0, stop]]

    # output
    crystal = sim.volume_manager.get_volume(f"spect_crystal")
    hits = sim.get_actor_user_info(f"Hits_{crystal.name}")
    singles = sim.get_actor_user_info(f"Singles_{crystal.name}")
    eb = sim.get_actor_user_info(f"Singles_{crystal.name}_eblur")
    sb = sim.get_actor_user_info(f"Singles_{crystal.name}_sblur")
    proj = sim.get_actor_user_info(f"Projection_{crystal.name}")
    stats = sim.get_actor_user_info("stats")
    hits.output = paths.output / "output_test2.root"
    singles.output = hits.output
    eb.output = hits.output
    sb.output = hits.output
    proj.output = paths.output / "projections_test2.mhd"
    stats.output = paths.output / "stats2.txt"

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
    print(paths)
    is_ok = compare_stats(output, paths.gate_output / f"stats2.txt")

    # Compare root files
    fr = paths.gate_output / "output2.root"
    stats = output.get_actor("stats")
    sn = f"Singles_{crystal.name}_sblur"
    is_ok = compare_root_singles(crystal, output, fr, paths.output, sn, n=2) and is_ok

    # compare images with Gate
    fr = paths.gate_output / "projection2.mhd"
    is_ok = compare_proj_images(crystal, output, stats, fr, paths.output, n=2) and is_ok
    utility.test_ok(is_ok)
