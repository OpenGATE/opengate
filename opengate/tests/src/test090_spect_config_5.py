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

    # units
    deg = g4_units.deg
    Bq = g4_units.Bq
    cm = g4_units.cm

    # make it FF scatter
    sc.free_flight_config.scatter_activity = 1e3 * Bq
    sc.free_flight_config.angle_tolerance = 15 * deg
    sc.free_flight_config.angle_tolerance_min_distance = 6 * cm
    sc.free_flight_config.max_compton_level = 5
    sc.free_flight_config.compton_splitting_factor = 20
    sc.free_flight_config.rayleigh_splitting_factor = 20

    # create the simulation
    sim = gate.Simulation()
    sim.random_seed = 123654987
    sc.setup_simulation_ff_scatter(sim, visu=False)
    stats = sim.actor_manager.find_actors("stats")[0]

    # go
    sim.run(start_new_process=True)

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(5409, sc, stats, is_ok)
    is_ok = check_projection_files(sim, paths, stats, is_ok)

    utility.test_ok(is_ok)
