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
    sc.source_config.remove_low_energy_lines = False  # FIXME
    sc.source_config.total_activity = 2e4 * Bq
    sc.free_flight_config.mode = "scatter"
    sc.free_flight_config.max_compton_level = 5
    sc.free_flight_config.compton_splitting_factor = 20
    sc.free_flight_config.rayleigh_splitting_factor = 20
    sc.free_flight_config.angular_acceptance.angle_tolerance_max = 15 * deg
    sc.free_flight_config.angular_acceptance.policy = "Rejection"
    sc.free_flight_config.angular_acceptance.skip_policy = "SkipEvents"
    sc.free_flight_config.angular_acceptance.enable_intersection_check = True
    sc.free_flight_config.angular_acceptance.enable_angle_check = True
    sc.free_flight_config.angular_acceptance.angle_check_proximity_distance = 6 * cm

    # create the simulation
    sim = gate.Simulation()
    sim.random_seed = 666
    sc.setup_simulation(sim, visu=False)
    print(sc)
    stats = sim.actor_manager.find_actors("stats")[0]

    # go
    sim.run(start_new_process=True)

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(108300, sc, stats, is_ok)
    is_ok = check_projection_files(
        sim,
        paths,
        stats,
        is_ok,
        tol=30,
        output_ref=paths.output_ref / "scatter",
        axis="x",
    )

    utility.test_ok(is_ok)
