#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *

# create the simulation
sim = gate.Simulation()
create_sim_test_region(sim)

# start simulation
sim.user_info.number_of_threads = 2
sim.run(False)

# print results at the end
stat = sim.output.get_actor("stats")
print(stat)

is_ok = True
gate.test_ok(is_ok)
