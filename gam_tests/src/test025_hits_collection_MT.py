#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import test025_hits_collection_base as t025

sim = t025.create_simulation(3)

sim.initialize()
sim.start()

t025.test_simulation_results(sim)
