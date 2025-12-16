#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test085_spect_ref"
    )

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 15
    # im.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ref",
        ac=5e6,
        use_spect_head=True,
        use_spect_arf=False,
        use_phsp=False,
    )

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # not really a test, generate reference simulation for FF
    utility.test_ok(True)
