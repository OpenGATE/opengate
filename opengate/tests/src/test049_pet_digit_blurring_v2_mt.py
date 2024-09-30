#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test049_pet_digit_blurring_helpers as t49
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test049_pet_blur", "test049")

    """
    see https://github.com/teaghan/PET_MonteCarlo
    and https://doi.org/10.1002/mp.16032

    PET simulation to test blurring options of the digitizer

    - PET:
    - phantom: nema necr
    - output: singles with and without various blur options
    """

    # create the simulation
    sim = gate.Simulation()
    nb_threads = 2
    t49.create_simulation(sim, nb_threads)

    # start simulation
    sim.run()

    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    # ----------------------------------------------------------------------------------------------------------
    readout = sim.get_actor("Singles")
    ig = readout.GetIgnoredHitsCount()
    print()
    print(f"Nb of ignored hits : {ig}")

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    p = paths.gate_output
    stats_ref = utility.read_stat_file(p / "stats.txt")
    stats_ref.counts.runs = nb_threads
    is_ok = utility.assert_stats(stats, stats_ref, 0.025)

    # check root hits
    hc = sim.get_actor("Hits")
    f = p / "pet.root"
    is_ok = (
        t49.check_root_hits(paths, 1, f, hc.get_output_path(), "test049_hits_v2_MT.png")
        and is_ok
    )

    # check root singles
    sc = sim.get_actor("Singles")
    is_ok = (
        t49.check_root_singles(
            paths, 1, f, sc.get_output_path(), png_output="test049_singles_v2_MT.png"
        )
        and is_ok
    )

    # gate.delete_run_manager_if_needed(sim) # no
    utility.test_ok(is_ok)
