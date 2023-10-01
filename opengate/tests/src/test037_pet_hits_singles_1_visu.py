#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test037_pet_hits_singles_helpers as t37
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test037_pet")

    """
    This test considers a PET system (Vereos Philips), with NEMA NECR linear fantom and source (F18).
    The digitizer is simplified to:
        1) hits collection
        2) singles are obtained with one simple adder (EnergyWeightedCentroidPosition)

    Note that this is not a correct digitizer (no blurring, no noise, no dead-time, etc).

    Hits are recorded into the crystal volumes (repeated 23,040 times).
    Singles are created by grouping hits from the same event, in the same crystal.

    The output is a root file composed of two trees 'Hits' and 'Singles'.
    Both are compared to an equivalent legacy Gate simulation.

    Salvadori J, Labour J, Odille F, Marie PY, Badel JN, Imbert L, Sarrut D.
    Monte Carlo simulation of digital photon counting PET.
    EJNMMI Phys. 2020 Apr 25;7(1):23.
    doi: 10.1186/s40658-020-00288-w

    """

    # create the simulation
    sim = gate.Simulation()
    crystal = t37.create_pet_simulation(sim, paths, debug=True)
    t37.add_digitizer(sim, paths, "1", crystal)

    # Visu
    sim.user_info.visu = True
    sim.user_info.visu_type = "gdml"
    sim.user_info.visu_filename = "geant4VisuFile.wrl"

    # timing
    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.000000005 * sec]]

    # start simulation
    sim.run()

    # print results
    stats = sim.output.get_actor("Stats")
    print(stats)

    # ----------------------------------------------------------------------------------------------------------

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    p = paths.gate / "output"
    stats_ref = utility.read_stat_file(p / "stats1.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.025)

    # check root hits
    hc = sim.output.get_actor("Hits").user_info
    f = p / "output1.root"
    is_ok = t37.check_root_hits(paths, 1, f, hc.output) and is_ok

    # check root singles
    sc = sim.output.get_actor("Singles").user_info
    is_ok = t37.check_root_singles(paths, 1, f, sc.output) and is_ok

    utility.test_ok(is_ok)
