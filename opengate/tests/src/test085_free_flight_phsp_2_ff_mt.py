#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff",
        ac=1e4,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # GeneralProcess must *NOT* be true (it is by default)
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    # AA, disabled here for the test (no need because the phsp covers 4 pi)
    source.direction.acceptance_angle.intersection_flag = False
    source.direction.acceptance_angle.normal_flag = False

    # free flight actor
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "phantom"

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_1_ff.root",
        paths.output / "phsp_1_ff.root",
        "phsp1",
        "phsp1",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ff.png",
    )

    utility.test_ok(is_ok)
