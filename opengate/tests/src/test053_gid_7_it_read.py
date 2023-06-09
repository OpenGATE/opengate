#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gid_helpers2 import *

paths = gate.get_default_test_paths(__file__, "", output_folder="test053")

# bi213 83 213
# ac225 89 225
# fr221 87 221
z = 89
a = 225
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

sim = gate.Simulation()
sim_name = f"{nuclide.nuclide}_7_model_read"
create_sim_test053(sim, sim_name)

# sources
activity_in_Bq = 1000
sim.user_info.number_of_threads = 2
sim.user_info.force_multithread_mode = True
s = add_source_model(sim, z, a, activity_in_Bq)
s.load_from_file = paths.output / f"test053_{nuclide.nuclide}_gamma.json"
s.atomic_relaxation_flag = False
s.isomeric_transition_flag = True

# go
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 5 * min
end_time = start_time + 20 * sec
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
output = sim.start(start_new_process=True)

# print stats
stats = output.get_actor("stats")
print(stats)

# compare
gate.warning(f"check root files")
root_ref = paths.output / f"test053_{nuclide.nuclide}_5_ref.root"
root_model = sim.get_actor_user_info("phsp").output
is_ok = compare_root_energy(
    root_ref, root_model, start_time, end_time, model_index=130, tol=0.09
)

gate.test_ok(is_ok)
