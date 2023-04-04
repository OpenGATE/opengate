#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from test053_gamma_from_ion_decay_helpers import *

paths = gate.get_default_test_paths(__file__, "")

sim = gate.Simulation()

# units
nm = gate.g4_units("nm")
m = gate.g4_units("m")
mm = gate.g4_units("mm")
km = gate.g4_units("km")
cm = gate.g4_units("cm")
Bq = gate.g4_units("Bq")

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.number_of_threads = 1
ui.visu = False
ui.random_seed = "auto"

# activity
sec = gate.g4_units("second")
duration = 100 * sec
activity = 1000 * Bq / ui.number_of_threads
if ui.visu:
    activity = 1 * Bq

# world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]
world.material = "G4_WATER"

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = True
sim.set_cut("world", "all", 1e6 * mm)

# sources
# ui.running_verbose_level = gate.EVENT
s1 = sim.add_source("GammaFromIonDecaySource", "ac225")
# s1.particle = "ion 89 225"  # Ac225
s1.particle = "ion 83 213"  # Bi213
s1.activity = activity
s1.position.type = "sphere"
s1.position.radius = 1 * nm
s1.position.translation = [0, 0, 0]
s1.direction.type = "iso"
s1.load_from_file = paths.output / "test053_bi213_gamma.json"
s1.tac_bins = 200
s1.dump_log = paths.output / "test053_bi213_gamma_read_log.txt"

# FIXME : add log source info ??

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True
s.output = paths.output / "test053_stats_source2.txt"

# phsp actor
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.attributes = ["KineticEnergy", "GlobalTime"]
phsp.output = paths.output / "test053_fast_source2.root"

f = sim.add_filter("ParticleFilter", "f1")
f.particle = "gamma"
phsp.filters.append(f)

# go
# ui.running_verbose_level = gate.EVENT
sim.run_timing_intervals = [[0, duration]]
output = sim.start()

# print stats
stats = output.get_actor("stats")
print(stats)

# compare
gate.warning(f"check root files")

# read root ref
f1 = paths.output / "test053_ref_ion_source.root"
root_ref = uproot.open(f1)
tree_ref = root_ref[root_ref.keys()[0]]

f2 = paths.output / "test053_fast_source2.root"
root = uproot.open(f2)
tree = root[root.keys()[0]]

# get gammas with correct timing
keV = gate.g4_units("keV")
ref_g = []
for batch in tree_ref.iterate():
    for e in batch:
        if e["GlobalTime"] < duration:
            ref_g.append(e["KineticEnergy"])

k = "KineticEnergy"
is_ok = gate.compare_branches_values(tree_ref[k], tree[k], k, k, tol=0.15)

# plot histo
print(f"Nb de gamma", len(ref_g))
f, ax = plt.subplots(1, 1, figsize=(15, 5))
ax.hist(ref_g, label=f"Reference root", bins=200)

g = []
for batch in tree.iterate():
    for e in batch:
        g.append(e["KineticEnergy"])

ax.hist(g, label=f"Fast source2", bins=200)

ax.legend()
# plt.show()
f = paths.output / "test053_fast_source_read.png"
print("Save figure in ", f)
plt.savefig(f)

with open(s1.dump_log, "r") as f:
    print(f.read())

gate.test_ok(is_ok)
