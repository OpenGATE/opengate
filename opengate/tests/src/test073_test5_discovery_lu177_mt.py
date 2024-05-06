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
    # sim.visu = True
    head, stats, source = test073_setup_sim(sim, "discovery", collimator_type="megp")
    sim.random_seed = 123456789

    # digit
    crystal = sim.volume_manager.get_volume(f"{head.name}_crystal")
    digit = discovery.add_digitizer_lu177(sim, crystal.name, "digit_lu177")
    ew = digit.find_first_module("energy_window")
    ew.output = paths.output / "output_discovery_lu177.root"

    # output
    stats.output = paths.output / "stats_discovery_lu177.txt"

    # source
    Bq = gate.g4_units.Bq
    set_source_rad_energy_spectrum(source, "lu177")
    source.activity = 3e8 * Bq / sim.number_of_threads

    # start simulation
    sim.run()
    output = sim.output

    # stat
    s = output.get_actor("stats")
    print(s)
    print(stats.output)

    # compare stats
    ref_folder = paths.output_ref
    is_ok = compare_stats(output, ref_folder / "stats_discovery_lu177.txt")

    # compare root
    fr = ref_folder / "output_discovery_lu177.root"
    is_ok = (
        compare_root_spectrum2(
            fr, ew.output, paths.output / "test073_discovery_lu177.png"
        )
        and is_ok
    )

    utility.test_ok(is_ok)
