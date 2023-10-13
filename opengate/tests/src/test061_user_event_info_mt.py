#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test061_user_event_info_helpers import create_simulation, analyse
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test061")

    # create the simulation
    sim = gate.Simulation()
    sim.user_info.number_of_threads = 1
    create_simulation(sim, paths, "mono")

    # run
    sim.run(start_new_process=True)

    # analyse 1
    is_ok = analyse(sim.output)

    # run in MT
    sim.number_of_threads = 2
    sim.run(start_new_process=True)

    # analyse 2
    is_ok = analyse(sim.output) and is_ok

    utility.test_ok(is_ok)
