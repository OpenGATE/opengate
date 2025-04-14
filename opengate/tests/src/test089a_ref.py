#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test089_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test089")

    # sim
    sim = gate.Simulation()
    sim.output_dir = paths.output
    stats, _, source = create_test089(sim, "test089_ref", visu=False)
    sim.number_of_threads = 8

    source.activity = 1e9 * gate.g4_units.Bq / sim.number_of_threads

    # go
    sim.run()
    print(stats)
