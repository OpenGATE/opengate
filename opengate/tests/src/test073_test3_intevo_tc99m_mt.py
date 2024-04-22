#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test073_helpers import *
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test073"
    )

    # create the simulation
    sim = gate.Simulation()
    head, stats, source = test073_setup_sim(sim, "intevo", collimator_type="lehr")
    sim.random_seed = 123456

    # digit
    crystal = sim.volume_manager.get_volume(f"{head.name}_crystal")
    digit = intevo.add_digitizer_tc99m(sim, crystal.name, "digit_tc99m")
    ew = digit.find_first_module("energy_window")
    ew.output = paths.output / "output_tc99m.root"

    # output
    stats.output = paths.output / "stats_intevo_tc99m.txt"

    # source
    Bq = gate.g4_units.Bq
    set_source_rad_energy_spectrum(source, "tc99m")
    source.activity = 2e7 * Bq / sim.number_of_threads

    # start simulation
    sim.run()
    output = sim.output

    # stat
    s = output.get_actor("stats")
    print(s)
    print(stats.output)

    # compare stats
    ref_folder = paths.output_ref
    is_ok = compare_stats(output, ref_folder / "stats_intevo_tc99m.txt")

    # compare root
    fr = ref_folder / "output_intevo_tc99m.root"
    is_ok = (
        compare_root_spectrum(fr, ew.output, paths.output / "test073_intevo_tc99m.png")
        and is_ok
    )

    utility.test_ok(is_ok)
