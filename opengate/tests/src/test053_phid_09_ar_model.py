#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_phid_helpers2 import *
import opengate as gate

if __name__ == "__main__":
    paths = get_default_test_paths(__file__, "", output_folder="test053")

    # bi213 83 213
    # ac225 89 225
    # fr221 87 221
    # pb 82 212
    # po 84 213
    # tl 81 209
    z = 81
    a = 209
    nuclide, _ = get_nuclide_and_direct_progeny(z, a)
    print(nuclide)
    sim_name = f"{nuclide.nuclide}_9_model"

    # this test need output/test053/test053_Tl-209_8_ref.root
    r = paths.output / f"test053_{nuclide.nuclide}_8_ref.root"
    if not os.path.exists(r):
        # ignore on windows
        if os.name == "nt":
            test_ok(True)
            sys.exit(0)
        cmd = "python " + str(paths.current / "test053_phid_08_ar_ref_mt.py")
        r = os.system(cmd)

    sim = gate.Simulation()
    create_sim_test053(sim, sim_name)

    # sources
    activity_in_Bq = 1000
    s = add_source_model(sim, z, a, activity_in_Bq)
    s.atomic_relaxation_flag = True
    s.isomeric_transition_flag = False

    # go
    sec = g4_units.second
    min = g4_units.minute
    start_time = 4 * min
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
    root_ref = paths.output / f"test053_{nuclide.nuclide}_8_ref.root"
    root_model = sim.get_actor("phsp").get_output_path()
    is_ok = compare_root_energy(
        root_ref, root_model, start_time, end_time, model_index=148, tol=0.015
    )

    test_ok(is_ok)
