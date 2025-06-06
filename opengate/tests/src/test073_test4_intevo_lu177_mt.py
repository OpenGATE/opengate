#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test073_helpers import *
from opengate.tests import utility
from opengate.sources.utility import set_source_energy_spectrum

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, gate_folder="", output_folder="test073"
    )

    # create the simulation
    sim = gate.Simulation()
    head, stats, source = test073_setup_sim(sim, "intevo", collimator_type="melp")
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # add a channel 'spectrum' (which is not by default because not compatible with ARF)
    keV = gate.g4_units.keV
    channels = intevo.get_default_energy_windows("lu177", False)
    c = {"name": "spectrum", "min": 35 * keV, "max": 588 * keV}
    channels.append(c)

    # digit
    crystal = sim.volume_manager.get_volume(f"{head.name}_crystal")
    digit = intevo.add_digitizer(
        sim, crystal.name, name="digit_lu177", channels=channels
    )
    ew = digit.find_module("energy_window")
    ew.output_filename = "output_intevo_lu177.root"
    ew.root_output.write_to_disk = True

    # output
    stats.output_filename = "stats_intevo_lu177.txt"

    # source
    Bq = gate.g4_units.Bq
    set_source_energy_spectrum(source, "Lu177", "radar")
    source.activity = 2e8 * Bq / sim.number_of_threads

    # start simulation
    sim.run()

    # stat
    print(stats)

    # FIXME ea.efficiency = 0.86481

    # compare stats
    ref_folder = paths.output_ref
    is_ok = compare_stats(sim, ref_folder / "stats_intevo_lu177.txt")

    # compare root
    fr = ref_folder / "output_intevo_lu177.root"
    is_ok = (
        compare_root_spectrum(
            fr, ew.get_output_path(), paths.output / "test073_intevo_lu177.png"
        )
        and is_ok
    )

    utility.test_ok(is_ok)
