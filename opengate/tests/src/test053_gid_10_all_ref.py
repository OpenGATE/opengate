#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gid_helpers2 import *
import os

paths = gate.get_default_test_paths(__file__, "", output_folder="test053")

# bi213 83 213
# ac225 89 225
# fr221 87 221
# pb 82 212
# po 84 213
# tl 81 209
z = 89
a = 225
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

sim = gate.Simulation()
sim_name = f"{nuclide.nuclide}_10_ref"
create_sim_test053(sim, sim_name, output=paths.output)

phsp = sim.get_actor_user_info("phsp")
phsp.filters = [phsp.filters[0]]
print(phsp.output)

p = sim.get_physics_user_info()
mm = gate.g4_units("mm")
sim.set_cut("world", "all", 1 * mm)

# sources
sim.user_info.number_of_threads = 4
activity_in_Bq = 500
add_source_generic(sim, z, a, activity_in_Bq)

# timing
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 15 * min
end_time = start_time + 2 * min
duration = end_time - start_time
print(f"start time {start_time / sec}")
print(f"end time {end_time / sec}")
print(f"Duration {duration / sec}")
print(f"Ions {activity_in_Bq * duration / sec:.0f}")
sim.run_timing_intervals = [[0, end_time]]

# go
output = sim.start(start_new_process=True)

# print stats
stats = output.get_actor("stats")
print(stats)

# compare with reference root file
gate.warning(f"check root files")
root_model = sim.get_actor_user_info("phsp").output
root_ref = paths.output_ref / os.path.basename(root_model)
keys = ["KineticEnergy", "TrackCreatorModelIndex"]
tols = [0.002, 0.04]
img = paths.output / str(root_model).replace(".root", ".png")
is_ok = gate.compare_root3(
    root_ref, root_model, "phsp", "phsp", keys, keys, tols, None, None, img
)

gate.test_ok(is_ok)
