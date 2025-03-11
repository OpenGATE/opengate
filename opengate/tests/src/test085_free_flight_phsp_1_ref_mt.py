#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ref",
        ac=5e4,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # GeneralProcess must *NOT* be true (it is by default)
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    # no AA for reference
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_1_ref.root",
        paths.output / "phsp_1_ref.root",
        "phsp1",
        "phsp1",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ref.png",
    )

    utility.test_ok(is_ok)
