#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.contrib.spect.spect_config import *
from test090_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_5"
    )

    # TEST 3: intevo, Lu177, 2 heads, 3 angles, with FF scatter
    sc = create_test_spect_config(paths)

    # create the simulation
    print(sc)
    sim = gate.Simulation()
    output = sc.create_simulation(sim, number_of_threads=1, visu=False)
    print(output)

    # make it FF-AA primary
    deg = g4_units.deg
    ac = 1e3 * g4_units.Bq / sim.number_of_threads
    if sim.visu:
        ac = 10 * g4_units.Bq
    crystals = sim.volume_manager.find_volumes("crystal")
    crystal_names = [c.name for c in crystals]
    options = Box(
        {
            "scatter_activity": ac,
            "angle_tolerance": 15 * deg,
            "volume_names": crystal_names,
            "angle_tolerance_min_distance": 6 * g4_units.cm,
            "max_compton_level": 5,
            "compton_splitting_factor": 20,
            "rayleigh_splitting_factor": 20,
        }
    )
    spect_freeflight_initialize_scatter(sim, sc, output.source, options)

    # run it
    sim.random_seed = "auto"
    sim.run()

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(5409, sc, output, is_ok)
    is_ok = check_projection_files(sim, paths, output, is_ok)

    utility.test_ok(is_ok)
