#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from matplotlib import pyplot as plt

from opengate import g4_units
from opengate.tests import utility
from test085_free_flight_helpers import *
import SimpleITK as sitk
import uproot

if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    #
    ref_filename = paths.output / "phsp_1_ref.root"
    prim_filename = paths.output / "phsp_1_ff.root"
    sca_filename = paths.output / "phsp_1_ff_sc.root"
    ref_n = 5e3
    prim_n = 5e3
    sca_n = 1e3
    scaling_sc = prim_n / sca_n

    # energy histo
    branch = "phsp1"
    k = "KineticEnergy"
    ene_ref = uproot.open(paths.output / ref_filename)[branch]
    ene_ref = ene_ref.arrays(library="numpy")[k]

    ene_prim = uproot.open(paths.output / prim_filename)[branch]
    ene_prim_w = ene_prim.arrays(library="numpy")["Weight"]
    ene_prim = ene_prim.arrays(library="numpy")[k]

    ene_sc = uproot.open(paths.output / sca_filename)[branch]
    ene_sc_w = ene_sc.arrays(library="numpy")["Weight"] * scaling_sc
    ene_sc = ene_sc.arrays(library="numpy")[k]

    print(f"Number of events, ref    = {len(ene_ref)}")
    print(f"Number of events, prim   = {len(ene_prim)}")
    print(f"Number of events, sc     = {len(ene_sc)}")
    print(f"scaling_sc               = {scaling_sc}")
    print(f"Sum of weights, prim     = {ene_prim_w.sum()}")
    print(f"Sum of weights, sec      = {ene_sc_w.sum()}")
    print(f"Sum of weights p+sec     = {ene_sc_w.sum()+ene_prim_w.sum()}")

    check1 = (len(ene_ref) - (ene_sc_w.sum() + ene_prim_w.sum())) / len(ene_ref) * 100
    is_ok = check1 < 2.0
    utility.print_test(is_ok, f"diff             p+sec     = {check1:.2f} % ")
    print(
        f"total rel diff ref-prim  = "
        f"{(len(ene_ref) - ene_prim_w.sum())/len(ene_ref)*100:.2f} %"
    )
    print(
        f"total rel diff ref-sec   = "
        f"{(len(ene_ref) - ene_sc_w.sum())/len(ene_ref)*100:.2f} %"
    )

    print()
    e_threshold = 0.140
    ene_ref_peak = ene_ref[ene_ref > e_threshold]
    print(f"Number of peaks ref      = {len(ene_ref_peak)}")
    print(f"Number of peaks prim     = {ene_prim_w.sum()}")
    d = len(ene_ref_peak) - ene_prim_w.sum()
    check2 = d / len(ene_ref_peak) * 100
    b = check2 < 6.0
    utility.print_test(b, f"rel diff peak ref-prim   = {check2:.2f} %  (d={d})")
    is_ok = b and is_ok

    ene_sc_peak = ene_sc[ene_sc > e_threshold]
    ene_sc_peak_w = ene_sc_w[ene_sc > e_threshold]
    print(f"Number of peaks sec      = {ene_sc_peak_w.sum()}")

    check3 = (d - ene_sc_peak_w.sum()) / d * 100
    b = check3 < 20.0
    utility.print_test(b, f"rel diff peaks ref-sc    = {check3:.2f} %")
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

    f = paths.output / "phsp_total_1.png"
    plt.legend()
    plt.savefig(f)
    print(f)
    plt.show()

    utility.test_ok(is_ok)
