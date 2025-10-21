#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
from opengate.tests import utility
from opengate.contrib.root_helpers import *
from opengate.sources.utility import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    # sim.visu = True
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ref",
        ac=1e5,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    rad_spectrum = get_spectrum("tc99m", "gamma", "radar")
    print(rad_spectrum)

    # split tree
    ref_root = paths.output_ref / "phsp_sphere_ref.root"
    highE_root = paths.output / "phsp_sphere_ref_peak.root"
    lowE_root = paths.output / "phsp_sphere_ref_scatter.root"
    print()
    print(
        f"Splitting tree in {paths.output_ref} into peak/scatter:\n"
        f"{highE_root}\n"
        f"{lowE_root}"
    )
    print()
    root_split_tree_by_branch(
        ref_root,
        highE_root,
        lowE_root,
        "phsp_sphere",
        "KineticEnergy",
        threshold=0.140511 * 0.999999,
        verbose=True,
    )

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_sphere_ref.root",
        paths.output / "phsp_sphere_ref.root",
        "phsp_sphere",
        "phsp_sphere",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ref.png",
    )

    # compare chi2
    """results, b = root_compare_branches_chi2(
        paths.output_ref / "phsp_sphere_ref.root",
        paths.output / "phsp_sphere_ref.root",
        "phsp_sphere",
        verbose=True,
    )
    utility.print_test(b, "Chi2 difference ? ")
    is_ok = is_ok and b"""

    fig = paths.output / "test085_phsp_ref2.png"
    root_plot_branch_comparison(
        paths.output_ref / "phsp_sphere_ref.root",
        paths.output / "phsp_sphere_ref.root",
        "phsp_sphere",
        save_path=fig,
    )
    print(f"Saved plot to {fig}")

    utility.test_ok(is_ok)
