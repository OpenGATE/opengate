#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gid_helpers2 import *
import os

paths = gate.get_default_test_paths(__file__, "", output_folder="test053")

# bi213 83 213
# ac225 89 225
# fr221 87 221
# lu177 71 177
z = 89
a = 225
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

sim = gate.Simulation()
sim_name = f"{nuclide.nuclide}_5_ref"
create_sim_test053(sim, sim_name)

# sources
sim.user_info.number_of_threads = 4
activity_in_Bq = 1000
add_source_generic(sim, z, a, activity_in_Bq)

# timing
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 0 * min
end_time = start_time + 20 * min
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

# compare with reference root file
gate.warning(f"check root files")
root_model = sim.get_actor_user_info("phsp").output
root_ref = paths.output_ref / os.path.basename(root_model)
keys = ["KineticEnergy", "TrackCreatorModelIndex"]
tols = [0.001, 0.02]
img = paths.output / str(root_model).replace(".root", ".png")
is_ok = gate.compare_root3(
    root_ref, root_model, "phsp", "phsp", keys, keys, tols, None, None, img
)

gate.test_ok(is_ok)
