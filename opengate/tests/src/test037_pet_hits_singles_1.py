#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test037_pet_hits_singles_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test037_pet")

"""
This test considers a PET system (Vereos Philips), with NEMA NECR linear fantom and source (F18).
The digitizer is simplified to:
    1) hits collection
    2) singles are obtained with one simple adder (EnergyWeightedCentroidPosition)

Note that this is not a correct digitizer (no blurring, no noise, no dead-time, etc).

Hits are recorded into the crystal volumes (repeated 23,040 times).
Singles are created by grouping hits from the same event, in the same crystal.

The output is a root file composed of two trees 'Hits' and 'Singles'.
Both are compared to an equivalent legacy Gate simulation.

Salvadori J, Labour J, Odille F, Marie PY, Badel JN, Imbert L, Sarrut D.
Monte Carlo simulation of digital photon counting PET.
EJNMMI Phys. 2020 Apr 25;7(1):23.
doi: 10.1186/s40658-020-00288-w

"""

# create the simulation
sim = gate.Simulation()
crystal = create_pet_simulation(sim, paths)
add_digitizer(sim, paths, "1", crystal)

# timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 0.00005 * sec]]

# start simulation
output = sim.start()

# print results
stats = output.get_actor("Stats")
print(stats)

# ----------------------------------------------------------------------------------------------------------

# check stats
print()
gate.warning(f"Check stats")
p = paths.gate / "output"
stats_ref = gate.read_stat_file(p / "stats1.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root hits
hc = output.get_actor("Hits").user_info
f = p / "output1.root"
is_ok = check_root_hits(paths, 1, f, hc.output) and is_ok

# check root singles
sc = output.get_actor("Singles").user_info
is_ok = check_root_singles(paths, 1, f, sc.output) and is_ok

gate.test_ok(is_ok)
