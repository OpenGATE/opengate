#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate import g4_units
from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    # sim.visu = True
    ac = 1e3
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff_sc",
        ac=ac,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # no AA for the source
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    ff = sim.add_actor("SplitComptonScatteringActor", "ff")
    ff.attached_to = "phantom"
    ff.splitting_factor = 10
    ff.max_compton_level = 10

    # no AA in this test (of course, it is inefficient)
    ff.acceptance_angle.skip_policy = "SkipEvents"
    ff.acceptance_angle.intersection_flag = False
    # ff.acceptance_angle.volumes = []  # ["spect_1"]  # , "spect_2"]
    ff.acceptance_angle.normal_flag = False
    ff.acceptance_angle.normal_vector = [0, 0, -1]
    ff.acceptance_angle.normal_tolerance = 10 * g4_units.deg

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_1_ff_sc.root",
        paths.output / "phsp_1_ff_sc.root",
        "phsp1",
        "phsp1",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ff_sc.png",
    )

    utility.test_ok(is_ok)
