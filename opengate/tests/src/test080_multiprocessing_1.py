#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from opengate.utility import g4_units
import opengate as gate
from opengate.tests.utility import get_default_test_paths



if __name__ == "__main__":
    paths = get_default_test_paths(
        __file__, output_folder="test080"
    )

    s = g4_units.s

    sim = gate.Simulation()
    sim.run_timing_intervals = [[0 * s, 1 * s], [1 * s, 3 * s], [10 * s, 15 * s]]
    sim.output_dir = paths.output
    sim.store_json_archive = True

    box1 = sim.add_volume("BoxVolume", "box1")
    box1.add_dynamic_parametrisation(
        translation=[[i, i, i] for i in range(len(sim.run_timing_intervals))]
    )

    n_proc = 4 * len(sim.run_timing_intervals)

    output = sim.run(number_of_sub_processes=n_proc)

    print("*** output ***")
    for o in output:
        print(o)

    print(f"ID of the main sim: {id(sim)}")

    ids = [o.simulation_id for o in output]
    assert id(sim) not in ids
