#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 8
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ref",
        ac=2e6,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # no AA for reference
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # s = f"/process/em/UseGeneralProcess false"
    # sim.g4_commands_before_init.append(s)

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # not really a test, generate reference simulation for FF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ref.mhd",
            paths.output / "projection_1_ref.mhd",
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
            paths.output_ref / "projection_2_ref.mhd",
            paths.output / "projection_2_ref.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=12,
            axis="x",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
