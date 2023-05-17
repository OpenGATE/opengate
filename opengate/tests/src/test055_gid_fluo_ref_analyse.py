#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt

from test054_gid_helpers2 import *
import opengate_core as g4

paths = gate.get_default_test_paths(__file__, "", output="test055")

# bi213 83 213
# ac225 89 225
# fr221 87 221
# pb 82 212
z = 82
a = 212
nuclide, _ = gate.get_nuclide_and_direct_progeny(z, a)
print(nuclide)

# go
activity_in_Bq = 1000
sec = gate.g4_units("second")
min = gate.g4_units("minute")
keV = gate.g4_units("keV")
start_time = 0 * min
end_time = start_time + 1e6 * min  # 10 * sec
duration = end_time - start_time
print(f"start time {start_time / sec}")
print(f"end time {end_time / sec}")
print(f"Duration {duration / sec}")
print(f"Ions {activity_in_Bq * duration / sec:.0f}")
sim.run_timing_intervals = [[start_time, end_time]]

sim_name_ref = f"{nuclide.nuclide}_ref"
f1 = paths.output / f"test054_{sim_name_ref}.root"
print(f1)
root_ref = uproot.open(f1)
tree_ref = root_ref[root_ref.keys()[0]]

"""
    TrackCreatorModelIndex
    index=130  model_RDM_IT  RadioactiveDecay
    index=148  model_RDM_AtomicRelaxation  RadioactiveDecay
"""
k = "KineticEnergy"
print("Nb entries", tree_ref.num_entries)
ref_g1 = tree_ref.arrays(
    ["KineticEnergy"],
    f"(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
    f"&(TrackCreatorModelIndex == 148)",
)[k]
print("Nb entries AtomicRelaxation", len(ref_g1))

ref_g2 = tree_ref.arrays(
    ["KineticEnergy"],
    f"(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
    f"&(TrackCreatorModelIndex == 130)",
)[k]
print("Nb entries IT", len(ref_g2))

ref_g3 = tree_ref.arrays(
    ["KineticEnergy"],
    f"(GlobalTime >= {start_time}) & (GlobalTime <= {end_time}) "
    f"&(TrackCreatorProcess == 'eBrem')",
)[k]
print("Nb entries Brem", len(ref_g3))

f, ax = plt.subplots(1, 1, figsize=(15, 5))
rg = [10, 100 * keV * 1000]
ax.hist(ref_g1 * 1000, label=f"AtomicRelaxation", bins=200, alpha=0.7, range=rg)
ax.hist(ref_g2 * 1000, label=f"Isomeric Transition", bins=200, alpha=0.7, range=rg)
ax.hist(ref_g3 * 1000, label=f"Brem", bins=200, alpha=0.7, range=rg)

ax.legend()
# plt.show()
# f = paths.output / f"test054_{sim_name}.png"
# print("Save figure in ", f)
# plt.savefig(f)
plt.show()
