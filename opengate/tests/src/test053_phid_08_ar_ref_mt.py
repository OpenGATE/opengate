#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test053_phid_helpers2 import *
import os
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

    sim = gate.Simulation()
    sim_name = f"{nuclide.nuclide}_8_ref"
    create_sim_test053(sim, sim_name, output=paths.output)

    phsp = sim.get_actor("phsp")
    phsp.filters = [phsp.filters[0]]
    print(phsp.output_filename)

    mm = g4_units.mm
    sim.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # sources
    sim.number_of_threads = 4
    activity_in_Bq = 1000
    add_source_generic(sim, z, a, activity_in_Bq)
    sim.random_seed = 123456

    # timing
    sec = g4_units.second
    min = g4_units.minute
    start_time = 0 * min
    end_time = start_time + 5 * min
    duration = end_time - start_time
    print(f"start time {start_time / sec}")
    print(f"end time {end_time / sec}")
    print(f"Duration {duration / sec}")
    print(f"Ions {activity_in_Bq * duration / sec:.0f}")
    sim.run_timing_intervals = [[0, end_time]]

    # go
    sim.run()

    # print stats
    stats = sim.get_actor("stats")
    print(stats)

    # compare with reference root file
    warning(f"check root files")
    root_model = sim.get_actor("phsp").get_output_path()
    root_ref = paths.output_ref / os.path.basename(root_model)
    keys = ["KineticEnergy", "TrackCreatorModelIndex"]
    tols = [0.002, 0.21]
    img = paths.output / str(root_model).replace(".root", ".png")
    is_ok = compare_root3(
        root_ref, root_model, "phsp", "phsp", keys, keys, tols, None, None, img
    )

    test_ok(is_ok)
