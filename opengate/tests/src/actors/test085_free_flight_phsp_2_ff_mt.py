#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *
from opengate.contrib.root_helpers import *
import subprocess

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # The test needs the output of the other tests
    if not os.path.isfile(paths.output / "phsp_sphere_ref_peak.root"):
        subdir = os.path.dirname(__file__)
        subprocess.call(
            ["python", paths.current / subdir / "test085_free_flight_phsp_1_ref_mt.py"]
        )

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 1
    # sim.visu = True
    ac = 1e4
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff",
        ac=ac,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # free flight actor
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "phantom"

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_sphere_ff.root",
        paths.output / "phsp_sphere_ff.root",
        "phsp_sphere",
        "phsp_sphere",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ff.png",
    )

    # NOTE: this MUST be slightly different, as the prim does not include part of the Rayl
    # that will come from the free flight scatter part.
    results, b = root_compare_branches_chi2(
        paths.output / "phsp_sphere_ref_peak.root",
        paths.output / "phsp_sphere_ff.root",
        "phsp_sphere",
        verbose=True,
    )
    utility.print_test(b, "Chi2 difference ? ")
    is_ok = is_ok and b

    fig = paths.output / "test085_phsp_prim.png"
    root_plot_branch_comparison(
        paths.output / "phsp_sphere_ref_peak.root",
        paths.output / "phsp_sphere_ff.root",
        "phsp_sphere",
        save_path=fig,
        scaling_factor2=1e5 / ac,
    )
    print(f"Saved plot to {fig}")

    """results = compare_branches_zscore(
        paths.output_ref / "phsp_sphere_ref_peak.root",
        paths.output / "phsp_sphere_ff.root",
        "phsp_sphere",
        # verbose=True,
        bins=10,
        scaling_factor2=1e5 / ac,
    )
    outliers = [r for r in results if "outliers" in r]
    b = len(outliers) == 4
    utility.print_test(b, f"Outliers ==4 ? {len(outliers)}")
    is_ok = is_ok and b"""

    utility.test_ok(is_ok)
