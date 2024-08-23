#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test025_hits_collection_helpers as t025

if __name__ == "__main__":
    sim = t025.create_simulation(3)
    sim.run()
    t025.test_simulation_results(sim)
