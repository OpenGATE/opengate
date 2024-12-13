#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
from opengate.tests import utility


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    create_simulation_test085(sim, paths, ac=5e5)

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # not really a test, generate reference simulation for FF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1.mhd",
            paths.output / "projection_1.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=12,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_2.mhd",
            paths.output / "projection_2.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=12,
            axis="x",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
