#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test054_gid_helpers2 import *

paths = gate.get_default_test_paths(__file__, "", output="test054")

# bi213 83 213
# ac225 89 225
# fr221 87 221
z = 89
a = 225
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

sim = gate.Simulation()
sim_name = f"{nuclide.nuclide}_model"
create_sim_test054(sim, sim_name)

# sources
activity_in_Bq = 1000
add_source_model(sim, z, a, activity_in_Bq)

# go
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 30 * min
end_time = start_time + 10 * sec
duration = end_time - start_time
print(f"start time {start_time / sec}")
print(f"end time {end_time / sec}")
print(f"Duration {duration / sec}")
print(f"Ions {activity_in_Bq * duration / sec:.0f}")
sim.run_timing_intervals = [[start_time, end_time]]

ui = sim.user_info
# ui.g4_verbose = True
# ui.running_verbose_level = gate.EVENT
# sim.apply_g4_command("/tracking/verbose 2")
output = sim.start()

# print stats
stats = output.get_actor("stats")
print(stats)

# compare
gate.warning(f"check root files")
sim_name_ref = f"{nuclide.nuclide}_ref"
is_ok = compare_root(sim_name_ref, sim_name, start_time, end_time)

gate.test_ok(is_ok)
