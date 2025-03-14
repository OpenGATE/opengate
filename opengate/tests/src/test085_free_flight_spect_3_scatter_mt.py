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
    sim.number_of_threads = 4
    ac = 4e4
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

    # free flight actor
    ff = sim.add_actor("ScatterSplittingFreeFlightActor", "ff")
    ff.attached_to = "phantom"
    ff.compton_splitting_factor = 50
    ff.rayleigh_splitting_factor = 10
    ff.max_compton_level = 10000
    ff.acceptance_angle.intersection_flag = True
    ff.acceptance_angle.volumes = ["spect_1"]  # FIXME check volume exists before
    ff.acceptance_angle.normal_flag = True
    ff.acceptance_angle.normal_vector = [0, 0, -1]
    ff.acceptance_angle.normal_tolerance = 10 * g4_units.deg

    # free flight actor
    ffc = sim.add_actor("GammaFreeFlightActor", "ffc")
    ffc.attached_to = "spect_1_collimator_trd"

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    print()
    print(ff)

    # compare to noFF
    is_ok = True
    is_ok = (
        utility.assert_images(
            paths.output_ref / "projection_1_ff_sc.mhd",
            paths.output / "projection_1_ff_sc.mhd",
            stats,
            tolerance=110,
            ignore_value_data1=0,
            sum_tolerance=10,
            sad_profile_tolerance=20,
            axis="x",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
