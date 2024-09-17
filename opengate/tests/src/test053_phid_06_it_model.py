#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_phid_helpers2 import *
import opengate as gate

if __name__ == "__main__":
    paths = get_default_test_paths(__file__, "", output_folder="test053")

    # bi213 83 213
    # ac225 89 225
    # fr221 87 221
    z = 89
    a = 225
    nuclide, _ = get_nuclide_and_direct_progeny(z, a)
    print(nuclide)

    # this test need the test053_phid_05 before
    root_ref = paths.output / f"test053_{nuclide.nuclide}_5_ref.root"
    if not os.path.exists(root_ref):
        # ignore on windows
        if os.name == "nt":
            test_ok(True)
            sys.exit(0)
        cmd = "python " + str(paths.current / "test053_phid_05_it_ref_mt.py")
        r = os.system(cmd)

    sim = gate.Simulation()
    sim_name = f"{nuclide.nuclide}_6_model"
    create_sim_test053(sim, sim_name)

    # sources
    activity_in_Bq = 1000
    s = add_source_model(sim, z, a, activity_in_Bq)
    s.atomic_relaxation_flag = False
    s.isomeric_transition_flag = True

    # go
    sec = g4_units.second
    min = g4_units.minute
    start_time = 19 * min
    end_time = start_time + 10 * sec
    duration = end_time - start_time
    print(f"start time {start_time / sec}")
    print(f"end time {end_time / sec}")
    print(f"Duration {duration / sec}")
    print(f"Ions {activity_in_Bq * duration / sec:.0f}")
    sim.run_timing_intervals = [[start_time, end_time]]

    # go
    sim.run(start_new_process=True)

    # print stats
    stats = sim.get_actor("stats")
    print(stats)

    # compare
    warning(f"check root files")
    root_ref = paths.output / f"test053_{nuclide.nuclide}_5_ref.root"
    root_model = sim.get_actor("phsp").get_output_path()
    is_ok = compare_root_energy(
        root_ref, root_model, start_time, end_time, model_index=130, tol=0.09
    )

    test_ok(is_ok)
