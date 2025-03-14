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
        ac=2e5,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # AA with acceptance angle
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.volumes = ["spect_1"]
    source.direction.acceptance_angle.normal_vector = [0, 0, -1]
    source.direction.acceptance_angle.normal_tolerance = 20 * gate.g4_units.deg

    # free flight actor
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "phantom"

    ff = sim.add_actor("GammaFreeFlightActor", "ff2")
    ff.attached_to = "spect_1_collimator_trd"

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare to noFF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ff.mhd",
            paths.output / "projection_1_ff.mhd",
            stats,
            tolerance=80,
            ignore_value_data1=0,
            sum_tolerance=10,
            sad_profile_tolerance=30,
            axis="x",
            fig_name=paths.output / "projection_ff_check_1.png",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
