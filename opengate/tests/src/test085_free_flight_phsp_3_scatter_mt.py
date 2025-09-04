#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test085_phsp")

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
    # warning : the interacting initial gamma are not killed when exist the phantom
    # we explicitly kill then when they go out
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

    # compare histo
    is_ok = utility.compare_root3(
        paths.output_ref / "phsp_sphere_ff_sc.root",
        paths.output / "phsp_sphere_ff_sc.root",
        "phsp_sphere",
        "phsp_sphere",
        keys1=None,
        keys2=None,
        tols=[0.01, 0.7, 1.4, 1.4, 0.01],
        scalings1=[1] * 5,
        scalings2=[1] * 5,
        img=paths.output / "test085_phsp_ff_sc.png",
    )

    utility.test_ok(is_ok)
