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
    ac = 5e4
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

    # no AA
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # free flight actor
    # need to NOT use generalProcess to enable only for Compton ? FIXME NO !
    # FIXME to change? to automatize ?
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    ff = sim.add_actor("SplitComptonScatteringActor", "ff")
    ff.attached_to = "phantom"
    ff.splitting_factor = 50
    ff.max_compton_level = 10

    ff.skip_policy = "SkipEvents"
    ff.intersection_flag = True
    ff.volumes = ["spect_1"]  # , "spect_2"] # FIXME dont use spect2 ftm
    ff.normal_flag = True
    ff.normal_vector = [0, 0, -1]
    ff.normal_tolerance = 10 * g4_units.deg

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

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
