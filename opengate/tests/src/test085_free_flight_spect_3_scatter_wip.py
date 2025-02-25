#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate import g4_units
from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect"
    )

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4  # FIXME
    ac = 1e4
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff_sc",
        ac=ac,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # no AA for the source
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # free flight actor
    ff = sim.add_actor("ComptonSplittingFreeFlightActor", "ff")
    ff.attached_to = "phantom"
    ff.splitting_factor = 50
    ff.max_compton_level = 10
    ff.acceptance_angle.skip_policy = "SkipEvents"
    ff.acceptance_angle.intersection_flag = True
    ff.acceptance_angle.volumes = [
        "spect_1"
    ]  # , "spect_2"]  # FIXME we dont use spect2 ftm
    ff.acceptance_angle.normal_flag = True
    ff.acceptance_angle.normal_vector = [0, 0, -1]
    ff.acceptance_angle.normal_tolerance = 10 * g4_units.deg

    # free flight actor
    """ff = sim.add_actor("GammaFreeFlightActor", "ffc")
    ff.attached_to = "spect_1_collimator_trd"
    """

    # go
    sim.number_of_threads = 1
    """sim.g4_verbose = True
    sim.g4_verbose_level = 1
    sim.g4_commands_after_init.append("/tracking/verbose 2")"""

    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    print()
    print(ff)

    # compare to noFF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1.mhd",
            paths.output / "projection_ff_sc_1.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=8.5,
            axis="x",
            scaleImageValuesFactor=5e5 / ac,
        )
        and is_ok
    )

    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_2.mhd",
            paths.output / "projection_ff_sc_2.mhd",
            stats,
            tolerance=65,
            ignore_value_data1=0,
            sum_tolerance=8.5,
            axis="x",
            scaleImageValuesFactor=5e5 / ac,
        )
        and is_ok
    )

    """is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_1.mhd",
            paths.output / "projection_ff_sc_1.mhd",
            stats,
            tolerance=30,
            ignore_value_data1=0,
            sum_tolerance=3,
            axis="x",
        )
        and is_ok
    )"""

    """is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_ff_sc_2.mhd",
            paths.output / "projection_ff_sc_2.mhd",
            stats,
            tolerance=30,
            ignore_value_data1=0,
            sum_tolerance=3,
            axis="x",
        )
        and is_ok
    )"""

    utility.test_ok(is_ok)
