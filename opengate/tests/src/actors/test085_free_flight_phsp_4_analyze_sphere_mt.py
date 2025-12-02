#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
from opengate.tests import utility
from opengate.contrib.root_helpers import *
from test085_free_flight_helpers import *
import uproot
import os, sys


def main(dependency="test085_free_flight_phsp_1_ref_mt.py"):

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # not on windows
    if os.name == "nt":
        sys.exit(0)

    # The test needs the output of the other tests
    subdir = os.path.dirname(__file__)
    if not os.path.isfile(paths.output / "phsp_sphere_ref.root"):
        subprocess.call(["python", paths.current / subdir / dependency])
    if not os.path.isfile(paths.output / "phsp_sphere_ff.root"):
        subprocess.call(
            ["python", paths.current / subdir / "test085_free_flight_phsp_2_ff_mt.py"]
        )
    if not os.path.isfile(paths.output / "phsp_sphere_ff_sc.root"):
        subprocess.call(
            [
                "python",
                paths.current / subdir / "test085_free_flight_phsp_3_scatter_mt.py",
            ]
        )

    # read root output
    ref_filename = paths.output / "phsp_sphere_ref.root"
    prim_filename = paths.output / "phsp_sphere_ff.root"
    sca_filename = paths.output / "phsp_sphere_ff_sc.root"
    ref_n = 1e5
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
    tol = 1.2
    b = np.fabs(check4) < tol
    utility.print_test(b, f"diff scatter ref-sc        = {check4:.2f} %    tol={tol}")
    is_ok = b and is_ok

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

    # merge prim + scatter in one root file
    merged_filename = paths.output / "phsp_total.root"
    root_merge_trees(
        (prim_filename, sca_filename),
        merged_filename,
        "phsp_sphere",
        scaling_factors=(ref_n / prim_n, ref_n / sca_n),
        verbose=True,
    )

    # compare with chi2 (must fail)
    # results, b = compare_branches_chi2(
    #    ref_filename, merged_filename, tree_name="phsp_sphere", verbose=True, bins=50
    # )
    # print(results)
    # utility.print_test(b, "Chi2 difference ? ")
    # is_ok = b and is_ok

    # compare with zscore
    """results = compare_branches_zscore(
        ref_filename, merged_filename, tree_name="phsp_sphere", verbose=True, bins=10
    )
    outliers = [r for r in results if "outliers" in r]
    print(f"Outliers : ", outliers)
    b = len(outliers) < 1
    utility.print_test(b, "Zscore difference ? ")
    is_ok = b and is_ok"""

    # compare with statistics
    results = compare_branches_statistics(
        ref_filename, merged_filename, tree_name="phsp_sphere", verbose=True
    )
    tol = 0.6  # %
    b = all(np.fabs(r["mean_diff_vs_std"]) < tol for r in results)
    utility.print_test(b, f"Statistics difference below {tol} ? ")
    is_ok = b and is_ok

    # NOPE because of weight
    """b = utility.compare_root3(
        ref_filename,
        merged_filename,
        "phsp_sphere",
        "phsp_sphere",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_4.png",
    )
    is_ok = b and is_ok"""

    # plot
    fig, axes = root_plot_branch_comparison(
        ref_filename,
        merged_filename,
        tree_name="phsp_sphere",
        verbose=True,
    )
    fn = paths.output / "test085_free_flight_phsp_4_merged.png"
    fig.savefig(fn)
    print(fn)

    utility.test_ok(is_ok)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    main()
