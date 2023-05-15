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
sim_name = f"{nuclide.nuclide}_model"
create_sim_test054(sim, sim_name)

# sources
activity_in_Bq = 1000
add_source_model(sim, z, a, activity_in_Bq)

# go
sec = gate.g4_units("second")
min = gate.g4_units("minute")
start_time = 10 * min
end_time = start_time + 30 * sec
duration = end_time - start_time
print(f"start time {start_time / sec}")
print(f"end time {end_time / sec}")
print(f"Duration {duration / sec}")
print(f"Ions {activity_in_Bq * duration / sec:.0f}")
sim.run_timing_intervals = [[start_time, end_time]]

ui = sim.user_info
# ui.g4_verbose = True
ui.running_verbose_level = gate.EVENT
# sim.apply_g4_command("/tracking/verbose 2")
output = sim.start()

# print stats
stats = output.get_actor("stats")
print(stats)

# compare
gate.warning(f"check root files")

# read root ref
f1 = paths.output / f"test054_{sim_name.replace('model', 'ref')}.root"
print(f1)
root_ref = uproot.open(f1)
tree_ref = root_ref[root_ref.keys()[0]]

f2 = paths.output / f"test054_{sim_name}.root"
print(f2)
root = uproot.open(f2)
tree = root[root.keys()[0]]

# get gammas with correct timing
keV = gate.g4_units("keV")
print("Nb entries", tree_ref.num_entries)
ref_g = tree_ref.arrays(
    ["KineticEnergy"],
    f"(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
    f"& (TrackCreatorModelIndex == 130)",
)
"""
    TrackCreatorModelIndex
    index=130  model_RDM_IT  RadioactiveDecay
    index=148  model_RDM_AtomicRelaxation  RadioactiveDecay
"""
print("Nb entries with correct range time", len(ref_g))

k = "KineticEnergy"
is_ok = gate.compare_branches_values(ref_g[k], tree[k], k, k, tol=0.01)

# plot histo
ref_g = ref_g[k]
print(f"Nb de gamma", len(ref_g))
f, ax = plt.subplots(1, 1, figsize=(15, 5))
ax.hist(ref_g, label=f"Reference root", bins=200, alpha=0.7)

g = tree.arrays(["KineticEnergy"])["KineticEnergy"]
ax.hist(g, label=f"Model source", bins=200, alpha=0.5)

ax.legend()
# plt.show()
f = paths.output / f"test054_{sim_name}.png"
print("Save figure in ", f)
plt.savefig(f)
plt.show()

gate.test_ok(is_ok)
