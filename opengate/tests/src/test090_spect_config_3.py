#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.contrib.spect.spect_config import *
from test090_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_3"
    )

    # TEST 3: intevo, Lu177, 2 heads, 3 angles, with FF-AA, primary only
    sc = create_test_spect_config(paths)

    # units
    deg = g4_units.deg
    Bq = g4_units.Bq
    cm = g4_units.cm

    # make it FFAA primary
    sc.free_flight_config.mode = "primary"
    sc.source_config.total_activity = 4e5 * Bq
    sc.free_flight_config.angular_acceptance.angle_tolerance_max = 15 * deg
    sc.free_flight_config.angular_acceptance.max_rejection = 10000
    sc.free_flight_config.angular_acceptance.policy = "Rejection"
    sc.free_flight_config.angular_acceptance.skip_policy = "SkipEvents"
    sc.free_flight_config.angular_acceptance.enable_intersection_check = True
    sc.free_flight_config.angular_acceptance.enable_angle_check = True

    # create the simulation
    sim = gate.Simulation()
    sim.random_seed = 123654
    sc.setup_simulation(sim, visu=False)
    stats = sim.actor_manager.find_actors("stats")[0]

    # go
    sim.run(start_new_process=True)

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(73826, sc, stats, is_ok)
    is_ok = check_projection_files(
        sim,
        paths,
        stats,
        is_ok,
        tol=100,
        squared_flag=True,
        output_ref=paths.output_ref / "primary",
        axis="x",
    )

    utility.test_ok(is_ok)
