#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
from matplotlib import pyplot as plt
from opengate.tests import utility
from test085_free_flight_helpers import *
import uproot
import os, sys


def main(dependency="test085_free_flight_phsp_1_ref_mt.py"):

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # not on windows
    if os.name == "nt":
        sys.exit(0)

    # The test needs the output of the other tests
    if not os.path.isfile(paths.output / "phsp_sphere_ref.root"):
        subprocess.call(["python", paths.current / dependency])
    if not os.path.isfile(paths.output / "phsp_sphere_ff.root"):
        subprocess.call(["python", paths.current / "test085_free_flight_phsp_2_ff.py"])
    if not os.path.isfile(paths.output / "phsp_sphere_ff_sc.root"):
        subprocess.call(
            ["python", paths.current / "test085_free_flight_phsp_3_scatter_mt.py"]
        )

    # read root output
    ref_filename = paths.output / "phsp_sphere_ref.root"
    prim_filename = paths.output / "phsp_sphere_ff.root"
    sca_filename = paths.output / "phsp_sphere_ff_sc.root"
    ref_n = 5e4
    prim_n = 1e4
    sca_n = 2e3
    scaling_sc = ref_n / sca_n
    scaling_prim = ref_n / prim_n

    # energy histo
    branch = "phsp_sphere"
    k = "KineticEnergy"
    ene_ref = uproot.open(paths.output / ref_filename)[branch]
    ene_ref = ene_ref.arrays(library="numpy")[k]

    ene_prim = uproot.open(paths.output / prim_filename)[branch]
    ene_prim_w = ene_prim.arrays(library="numpy")["Weight"] * scaling_prim
    ene_prim = ene_prim.arrays(library="numpy")[k]

    ene_sc = uproot.open(paths.output / sca_filename)[branch]
    ene_sc_w = ene_sc.arrays(library="numpy")["Weight"] * scaling_sc
    ene_sc = ene_sc.arrays(library="numpy")[k]

    print(
        f"Number of events, ref    = {len(ene_ref)}  {np.min(ene_ref):.2f} {np.max(ene_ref):.2f}"
    )
    print(
        f"Number of events, prim   = {len(ene_prim)} {np.min(ene_prim):.2f} {np.max(ene_prim):.2f}"
    )
    print(
        f"Number of events, sc     = {len(ene_sc)} {np.min(ene_sc):.2f} {np.max(ene_sc):.2f}"
    )
    print(f"scaling_prim             = {scaling_prim}")
    print(f"scaling_sc               = {scaling_sc}")

    print()
    print("==== TOTAL")
    print(f"Sum of weights, prim     = {ene_prim_w.sum():.0f}")
    print(f"Sum of weights, sec      = {ene_sc_w.sum():.0f}")
    t = ene_sc_w.sum() + ene_prim_w.sum()
    print(f"Sum of weights, p+sec    = {t:.0f} vs {len(ene_ref)}")

    check1 = (len(ene_ref) - (ene_sc_w.sum() + ene_prim_w.sum())) / len(ene_ref) * 100
    tol = 1.0
    is_ok = np.fabs(check1) < tol
    utility.print_test(
        is_ok, f"diff p+sec               = {check1:.2f} %     tol={tol:.2f}"
    )
    print(
        f"total rel diff ref-prim  = "
        f"{(len(ene_ref) - ene_prim_w.sum())/len(ene_ref)*100:.2f} %"
    )
    print(
        f"total rel diff ref-sec   = "
        f"{(len(ene_ref) - ene_sc_w.sum())/len(ene_ref)*100:.2f} %"
    )

    print()
    e_threshold = 0.14051  # 0.140511
    ene_ref_peak = ene_ref[ene_ref >= e_threshold]
    ene_sc_peak_w = ene_sc_w[ene_sc >= e_threshold]
    print("==== PEAK")
    print(f"Number of peaks ref      = {len(ene_ref_peak)}")
    print(f"Number of peaks prim     = {ene_prim_w.sum():.0f}")
    print(f"Number of peaks sec      = {ene_sc_peak_w.sum():.0f}")
    d = len(ene_ref_peak) - ene_prim_w.sum()
    check2 = d / len(ene_ref_peak) * 100
    tol = 10.0
    b = np.fabs(check2) < tol and np.fabs(check2) > 2
    utility.print_test(
        b,
        f"diff peak ref-prim       = {check2:.2f} %  (diff={d:.0f}) tol={tol} and >2%",
    )
    is_ok = b and is_ok

    # add the peak from the scatter (should be low)
    d = len(ene_ref_peak) - (ene_prim_w.sum() + ene_sc_peak_w.sum())
    check3 = d / len(ene_ref_peak) * 100
    tol = 1.0
    b = np.fabs(check3) < tol
    utility.print_test(b, f"diff peaks ref-(p+sc)    = {check3:.2f} %    tol={tol}")
    is_ok = b and is_ok

    # scatter
    print()
    print("==== SCATTER")
    ene_ref_scatter = ene_ref[ene_ref < e_threshold]
    ene_prim_w_scatter = ene_prim_w[ene_prim < e_threshold]  # should be almost zero
    ene_sc_w_scatter = ene_sc_w[ene_sc < e_threshold]
    print(f"Number of scatter ref      = {len(ene_ref_scatter)}")
    print(f"Number of scatter prim     = {ene_prim_w_scatter.sum():.0f}")
    print(f"Number of scatter sec      = {ene_sc_w_scatter.sum():.0f}")
    d = len(ene_ref_scatter) - (ene_sc_w_scatter.sum() + ene_prim_w_scatter.sum())
    check4 = d / len(ene_ref_scatter) * 100
    tol = 1.0
    b = np.fabs(check4) < tol
    utility.print_test(b, f"diff scatter ref-sc        = {check4:.2f} %    tol={tol}")
    is_ok = b and is_ok

    # Key KineticEnergy min/mean/max: 0.08349965517188826 0.1404070326435755 0.140511

    ene_total = np.concatenate((ene_prim, ene_sc))
    w_total = np.concatenate((ene_prim_w, ene_sc_w))

    fig = plt.figure()
    ax = fig.add_subplot(111)
    bins = 100
    d = False
    r = (0.0, 0.145)
    ax.hist(ene_ref, bins=bins, alpha=0.5, density=d, label="ref", range=r)
    ax.hist(
        ene_prim,
        bins=bins,
        alpha=0.5,
        density=d,
        range=r,
        weights=ene_prim_w,
        label="prim",
    )
    ax.hist(
        ene_sc, bins=bins, range=r, weights=ene_sc_w, alpha=0.5, density=d, label="sc"
    )

    ax.hist(
        ene_total,
        bins=bins,
        range=r,
        weights=w_total,
        alpha=0.2,
        density=d,
        label="total",
        histtype="stepfilled",
    )

    f = paths.output / "phsp_total.png"
    plt.legend()
    plt.savefig(f)
    print(f)
    # plt.show()

    utility.test_ok(is_ok)
