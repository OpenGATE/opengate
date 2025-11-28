#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *
from opengate.contrib.root_helpers import *
import subprocess

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

    # The test needs the output of the other tests
    if not os.path.isfile(paths.output / "phsp_sphere_ref_scatter"):
        subdir = os.path.dirname(__file__)
        subprocess.call(
            ["python", paths.current / subdir / "test085_free_flight_phsp_1_ref_mt.py"]
        )

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    # sim.visu = True
    ac = 2e3
    source, actors = create_simulation_test085(
        sim,
        paths,
        simu_name="ff_sc",
        ac=ac,
        use_spect_head=False,
        use_spect_arf=False,
        use_phsp=True,
    )

    # ff scatter: for this test, this is very inefficient
    # we only check the potential bias
    ff = sim.add_actor("ScatterSplittingFreeFlightActor", "ff")
    ff.attached_to = "world"  # Warning, if "phantom": cannot kill outside the phantom
    # warning: the interacting initial gammas are not killed when they are exiting the phantom
    # we explicitly kill then when they arrive in the phsp sphere
    ff.kill_interacting_in_volumes = ["phsp_sphere"]
    ff.compton_splitting_factor = 4  # the value must have no effect
    ff.rayleigh_splitting_factor = 4  # the value must have no effect
    ff.max_compton_level = 1000  # count everything

    # go
    sim.run(start_new_process=True)
    stats = sim.get_actor("stats")
    print(stats)

    print()
    print("Info during splitting")
    print(ff)

    # compare
    ref_root = paths.output / "phsp_sphere_ref_scatter.root"
    sc_root = paths.output / "phsp_sphere_ff_sc.root"
    results, _ = root_compare_branches_chi2(
        ref_root, sc_root, tree_name="phsp_sphere", verbose=True
    )
    print()
    b = all(not r["significant"] for r in results if r["branch"] != "KineticEnergy")
    r = [r for r in results if r["branch"] == "KineticEnergy"][0]
    print(r)
    b = r["significant"] == True and b
    utility.print_test(
        b, "Chi2 difference ? Should be only significant for KineticEnergy"
    )
    is_ok = b

    # print only
    """compare_branches_statistics(
        ref_root,
        sc_root,
        tree_name="phsp_sphere",
        verbose=True,
        scaling_factor2=1e5 / ac,
    )

    # zscore ? print only
    results = compare_branches_zscore(
        ref_root,
        sc_root,
        tree_name="phsp_sphere",
        verbose=True,
        scaling_factor2=1e5 / ac,
    )"""

    # plot
    fig, axes = root_plot_branch_comparison(
        ref_root,
        sc_root,
        tree_name="phsp_sphere",
        verbose=True,
        scaling_factor2=1e5 / ac,
    )
    fn = paths.output / "test085_free_flight_phsp_3_scatter.png"
    fig.savefig(fn)
    print()
    print(fn)

    utility.test_ok(is_ok)
