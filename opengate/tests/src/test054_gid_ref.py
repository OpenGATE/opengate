#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test054_gid_helpers import *

paths = gate.get_default_test_paths(__file__, "", output="test054")

# bi213 83 213
# ac225 89 225
# fr221 87 221
z = 89
a = 225
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

sim = gate.Simulation()
sim_name = f"{nuclide.nuclide}_ref"
create_sim_test054(sim, sim_name)

# sources
sim.user_info.number_of_threads = 4
activity_in_Bq = 1000
add_source_generic(sim, z, a, activity_in_Bq)

# timing
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 0 * min
end_time = start_time + 100 * min
duration = end_time - start_time
print(f"start time {start_time / sec}")
print(f"end time {end_time / sec}")
print(f"Duration {duration / sec}")
print(f"Ions {activity_in_Bq * duration / sec:.0f}")
sim.run_timing_intervals = [[0, end_time]]

# go
ui = sim.user_info
# ui.g4_verbose = True
# ui.running_verbose_level = gate.EVENT
# sim.apply_g4_command("/tracking/verbose 2")
output = sim.start()

# print stats
stats = output.get_actor("stats")
print(stats)
