#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot


def test_half_life_fit(sim, output, half_life, ax):
    sec = gate.g4_units.s
    keV = gate.g4_units.keV

    print(f"root file {output}")

    root = uproot.open(output)
    branch_name = root.keys()[0]
    branch = root[branch_name]["GlobalTime"]
    time = branch.array(library="numpy") / sec
    branch = root[branch_name]["KineticEnergy"]
    E = branch.array(library="numpy")

    # consider time of arrival for both peaks
    time1 = time[(E > 150 * keV) & (E < 250 * keV)]
    print(f"Total number of gammas           = {len(time1)}")

    tmax = sim.run_timing_intervals[1][1] / sec
    time2 = time1[time1 < tmax]
    print(f"Number of gammas from 0 to {tmax} sec = {len(time2)}")

    # fit for half life
    start_time = sim.run_timing_intervals[0][0] / sec
    end_time = sim.run_timing_intervals[0][1] / sec
    hl, xx, yy = utility.fit_exponential_decay(time1, start_time, end_time)
    # compare with source half_life (convert in sec)
    tol = 0.09
    hl_ref = half_life / sec
    diff = abs(hl - hl_ref) / hl_ref
    b = diff < tol
    diff *= 100
    utility.print_test(b, f"Half life {hl_ref:.2f} sec vs {hl:.2f} sec : {diff:.2f}% ")

    ax.hist(
        time1,
        bins=100,
        label="decay source",
        histtype="stepfilled",
        alpha=0.5,
        range=(0, sim.run_timing_intervals[1][1] / sec + 10),
        density=True,
    )
    ax.plot(xx, yy, label="fit half-life {:.2f} sec".format(hl))
    ax.legend()
    ax.set_xlabel("time (s)")
    ax.set_ylabel("produced gammas")

    return b, len(time2)
