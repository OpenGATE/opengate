#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    create_simulation_test085(sim, paths, ac=2e5)

    arf1 = sim.get_actor("detector_arf_1")
    arf2 = sim.get_actor("detector_arf_2")
    arf1.output_filename = f"projection_ff_1.mhd"
    arf2.output_filename = f"projection_ff_2.mhd"

    stats = sim.get_actor("stats")
    stats.output_filename = "stats_ff.txt"
    sim.json_archive_filename = "simu_ff.json"

    # free flight actor
    ff = sim.add_actor("FreeFlightActor", "ff")
    ff.attached_to = "phantom"
    ff.particles = "gamma"

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare to noFF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1.mhd",
            paths.output / "projection_ff_1.mhd",
            stats,
            tolerance=150,
            ignore_value_data1=0,
            sum_tolerance=8,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_2.mhd",
            paths.output / "projection_ff_2.mhd",
            stats,
            tolerance=150,
            ignore_value_data1=0,
            sum_tolerance=8,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_1.mhd",
            paths.output / "projection_ff_1.mhd",
            stats,
            tolerance=150,
            ignore_value_data1=0,
            sum_tolerance=8,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_2.mhd",
            paths.output / "projection_ff_2.mhd",
            stats,
            tolerance=150,
            ignore_value_data1=0,
            sum_tolerance=8,
            axis="x",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
