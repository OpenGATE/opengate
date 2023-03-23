#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_gamma_from_ion_decay_helpers import *
import matplotlib.pyplot as plt
import radioactivedecay as rd

paths = gate.get_default_test_paths(__file__, "")

# ac225
z = 89
a = 225

# bi213
z = 83
a = 213

sim = gate.Simulation()
ion_name, _ = create_ion_gamma_simulation(sim, paths, z, a)
nuclide = gate.get_nuclide(ion_name)
daughters = gate.get_all_nuclide_progeny(nuclide)
# daughters = [d.nuclide.nuclide for d in daughters]
# daughters = [d.replace('-', '') for d in daughters]
print()
for d in daughters:
    print(d)

phsp = sim.get_actor_user_info("phsp")


def rm_type(name, phsp):
    fg = sim.add_filter("ParticleFilter", f"fp_{name}")
    fg.particle = name
    fg.policy = "discard"
    phsp.filters.append(fg)


phsp.attributes = ["ParticleName", "ParticleType", "GlobalTime"]
rm_type("gamma", phsp)
rm_type("anti_nu_e", phsp)
rm_type("alpha", phsp)
rm_type("e-", phsp)
filename = phsp.output

Bq = gate.g4_units("Bq")
sec = gate.g4_units("second")
min = gate.g4_units("min")
h = gate.g4_units("h")

source = sim.get_source_user_info(ion_name)
source.activity = 5 * Bq
# source.activity = 0
# source.half_life = 2735.4 * sec ## Bi213
source.half_life = 10 * 24 * h  ##
# source.half_life = 2 * sec
# source.half_life = -1
# source.n = 1000

ui = sim.user_info
# ui.g4_verbose = True
# sim.apply_g4_command("/tracking/verbose 2")
km = gate.g4_units("km")
sim.set_cut("world", "all", 10 * km)

# --------------------------------------------------------------------------
# go
end = 1 * h
sim.run_timing_intervals = [[0, end]]
output = sim.start()
end = end / sec
# --------------------------------------------------------------------------

# print
stats = output.get_actor("stats")
print(stats)

# analyse
root = uproot.open(filename)
tree = root[root.keys()[0]]
print(f"Root tree {root.keys()} n={tree.num_entries}")
print(f"Keys:{tree.keys()}")

# group by ion
time_by_ion = {}
for batch in tree.iterate():
    for e in batch:
        if e["ParticleType"] != "nucleus":
            continue
        n = e["ParticleName"]
        if "[" in n:
            continue
        if n not in time_by_ion:
            time_by_ion[n] = []
        t = e["GlobalTime"] / sec
        if t < end:
            time_by_ion[n].append(t)

# group all ions channels WARNING use the parent !
time_by_ion_final = {}

print("root parsing")
for d in time_by_ion:
    print(d, len(time_by_ion[d]))

print()
for dd in time_by_ion.keys():
    # print(f"consider {dd}  {len(time_by_ion[dd])}")
    if "[" in dd:
        continue
    for d in daughters:
        name = d.nuclide.nuclide.replace("-", "")
        if name in dd:
            for parent in d.parent:
                if parent is None:
                    continue
                pname = parent.nuclide.replace("-", "")
                if pname not in time_by_ion_final:
                    time_by_ion_final[pname] = []
                # print(f"\t add {dd} in {name}->{pname}  parent = {d.parent}")
                time_by_ion_final[pname] += time_by_ion[dd]

print()
for d in time_by_ion_final:
    print(d, len(time_by_ion_final[d]))

lines_colour_cycle = [p["color"] for p in plt.rcParams["axes.prop_cycle"]]
# print(lines_colour_cycle)
colors = {}
i = 0
for d in daughters:
    n = d.nuclide.nuclide.replace("-", "")
    colors[n] = lines_colour_cycle[i]
    # print(n, colors[n])
    i += 1

fig, ax = plt.subplots(1, 2, figsize=(15, 5))
a = max(source.activity / Bq, source.n)
print("activity ", a)
inv = rd.Inventory({nuclide.nuclide: a}, "Bq")

inv.plot(
    end,
    "s",
    yunits="Bq",
    fig=fig,
    axes=ax[0],
    alpha=0.2,
    linewidth=8,
    order="dataset",
)

i = 0
bins = 200
f = bins / end
for d in daughters:  # time_by_ion_final:
    n = d.nuclide.nuclide.replace("-", "")
    if n in time_by_ion_final:
        x = time_by_ion_final[n]
        # print(d, len(x), colors[n])
        ax[0].hist(
            x,
            histtype="step",
            bins=bins,
            weights=f * np.ones_like(x),
            label=f"{n}",
            range=[0, end],
            # cumulative=True,
            # density=True, # NO
            color=colors[n],
        )
    i += 1

ax[0].legend()
ax[0].legend()

plt.show()
