#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test025_hits_collection_helpers as t025
from pathlib import Path

if __name__ == "__main__":
    sim = t025.create_simulation(1)
    sim.output_dir /= Path(__file__.rstrip(".py")).stem

    sim.run()

    t025.test_simulation_results(sim.output)
