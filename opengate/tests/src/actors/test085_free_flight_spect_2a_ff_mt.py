#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *
from opengate.contrib.spect.spect_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # create the simulation
    sim = gate.Simulation()
    # sim.visu = True
    sim.number_of_threads = 4
    ac = 2e5
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff",
        ac=ac,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # FF with Acceptance Angle
    source.direction.angular_acceptance.policy = "Rejection"
    source.direction.angular_acceptance.skip_policy = "SkipEvents"
    source.direction.angular_acceptance.enable_intersection_check = True
    source.direction.angular_acceptance.enable_angle_check = True
    source.direction.angular_acceptance.target_volumes = ["spect_1"]
    source.direction.angular_acceptance.angle_check_reference_vector = [0, 0, -1]
    source.direction.angular_acceptance.angle_tolerance_max = 20 * gate.g4_units.deg

    # free flight actor
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.exclude_volumes = ["spect_1_crystal"]

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # uncertainty
    uncer, _, _ = compute_history_by_history_relative_uncertainty_from_files(
        paths.output / "projection_1_ff_counts.mhd",
        paths.output / "projection_1_ff_squared_counts.mhd",
        ac,
        paths.output / "projection_1_ff_uncertainty.mhd",
    )

    # compare to noFF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ff_counts.mhd",
            paths.output / "projection_1_ff_counts.mhd",
            stats,
            tolerance=80,
            ignore_value_data1=0,
            sum_tolerance=14,
            sad_profile_tolerance=32,
            scaleImageValuesFactor=2e5 / ac,
            axis="x",
            fig_name=paths.output / "projection_ff_check_1.png",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
