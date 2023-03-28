#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

from test053_gamma_from_ion_decay_helpers import *
import matplotlib.pyplot as plt
import radioactivedecay as rd

paths = gate.get_default_test_paths(__file__, "")

# ac225
z = 89
a = 225

# bi213
# z = 83
# a = 213

# create simulation
sim = gate.Simulation()
ion_name, _ = create_ion_gamma_simulation(sim, paths, z, a)

# get list of nuclide organized per ion
nuclide = gate.get_nuclide(ion_name)
decay_list = gate.get_all_nuclide_progeny(nuclide)
decay_list_per_ion = {}
for d in decay_list:
    decay_list_per_ion[d.nuclide.nuclide.replace("-", "")] = d
for d in decay_list_per_ion:
    print(d, decay_list_per_ion[d])

# change simulation parameters
Bq = gate.g4_units("Bq")
sec = gate.g4_units("s")
h = gate.g4_units("h")
activity = 10 * Bq
end = 1 * h
update_sim_for_tac(sim, ion_name, nuclide, activity, end)

# --------------------------------------------------------------------------
# go
output = sim.start()
end = end / sec
# --------------------------------------------------------------------------

# print
stats = output.get_actor("stats")
print(stats)

# analyse
time_by_ion_final = analyse_time_per_ion_root(sim, end)

# plot
lines_colour_cycle = [p["color"] for p in plt.rcParams["axes.prop_cycle"]]
colors = {}
i = 0
rad_list = []
for d in decay_list:
    if d.hl == float("inf"):
        continue
    rad_list.append(d.nuclide.nuclide)
    n = d.nuclide.nuclide.replace("-", "")
    colors[n] = lines_colour_cycle[i]
    i += 1

fig, ax = plt.subplots(1, 1, figsize=(20, 10))
inv = rd.Inventory({nuclide.nuclide: activity / Bq}, "Bq")

inv.plot(
    end,
    "s",
    yunits="Bq",
    fig=fig,
    axes=ax,
    alpha=0.2,
    linewidth=8,
    order="dataset",
    display=rad_list,
)

i = 0
bins = 200

# random check ?
check = [0.10, 0.20, 0.50, 0.7]
check_dc = []
for c in check:
    dc = inv.decay(end * c, "s")
    check_dc.append(dc)

is_ok = True
for ion_name in decay_list_per_ion:
    # print(f'ion {ion_name}')
    b = decay_list_per_ion[ion_name]
    daughters = b.nuclide.progeny()
    branching_fractions = nuclide.branching_fractions()
    x = np.array([])
    for d, br in zip(daughters, branching_fractions):
        d_name = d.replace("-", "")
        a = np.array(time_by_ion_final[d_name])
        # print(f'\t {d_name} {b.intensity} x={len(x)} a={len(a)}')
        x = np.concatenate((x, a))

    if len(x) == 0:
        continue
    col = colors[ion_name]
    w = np.ones_like(x) * b.intensity
    hist, bin_edges = np.histogram(x, bins=bins, range=[0, end], weights=w)
    dx = bin_edges[1] - bin_edges[0]
    hist = hist / dx
    ax.stairs(hist, bin_edges, label=f"{ion_name}", color=col)

    # check
    i = 0
    n = b.nuclide.nuclide
    tol = 30
    for c in check:
        index = int(bins * c)
        ac = check_dc[i].activities("Bq")[n]
        if ac < 1:
            tol = 500
        diff = np.fabs(ac - hist[index]) / ac * 100.0
        ok = diff < tol
        gate.print_test(
            ok,
            f"check {ion_name} time={end * c:.2f}   ref = {ac:.2f} vs {hist[index]:.2f} ->  {diff:.2f}  (tol = {tol:.2f}%)",
        )
        is_ok = ok and is_ok
        i += 1

ax.legend()
# plt.show()

f = paths.output / "test053_gamma_from_ion_decay_tac_ac225.png"
print(f"Plot save in {f}")
plt.savefig(f)

gate.test_ok(is_ok)
