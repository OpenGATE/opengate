#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # create the simulation
    sim = gate.Simulation()
    # sim.visu = True
    sim.number_of_threads = 4
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff",
        ac=5e5,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # AA
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.normal_flag = True

    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

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
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=8.5,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_2.mhd",
            paths.output / "projection_ff_2.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=8.5,
            axis="x",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_1.mhd",
            paths.output / "projection_ff_1.mhd",
            stats,
            tolerance=30,
            ignore_value_data1=0,
            sum_tolerance=3,
            axis="x",
            fig_name=paths.output / "projection_ff_check_1",
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_2.mhd",
            paths.output / "projection_ff_2.mhd",
            stats,
            tolerance=30,
            ignore_value_data1=0,
            sum_tolerance=3,
            axis="x",
            fig_name=paths.output / "projection_ff_check_2",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
