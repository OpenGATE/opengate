#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test043_garf_helpers import *
import opengate.contrib.spect_ge_nm670 as gate_spect

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "gate_test043_garf")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 1
    ui.visu = False
    ui.random_seed = 123654

    # activity
    activity = 1e6 * Bq / ui.number_of_threads

    # world size
    sim_set_world(sim)

    # spect head
    spect, cystal = gate_spect.add_ge_nm67_spect_head(
        sim, "spect", collimator_type="lehr", debug=ui.visu
    )
    crystal_name = f"{spect.name}_crystal"

    # detector input plane
    pos, crystal_dist, psd = gate_spect.get_plane_position_and_distance_to_crystal(
        "lehr"
    )
    pos += 1 * nm  # to avoid overlap
    print(f"plane position     {pos / mm} mm")
    print(f"crystal distance   {crystal_dist / mm} mm")
    detPlane = sim_add_detector_plane(sim, spect.name, pos)

    # physics
    sim_phys(sim)

    # source
    s1 = sim.add_source("GenericSource", "s1")
    s1.particle = "gamma"
    s1.activity = activity
    s1.position.type = "disc"
    s1.position.radius = 57.6 * cm / 4  # FIXME why ???
    s1.position.translation = [0, 0, 12 * cm]
    s1.direction.type = "iso"
    s1.energy.type = "range"
    s1.energy.min_energy = 0.01 * MeV
    s1.energy.max_energy = 0.154 * MeV
    s1.direction.acceptance_angle.volumes = [detPlane.name]
    s1.direction.acceptance_angle.intersection_flag = True

    # digitizer
    channels = [
        {"name": f"scatter_{spect.name}", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140_{spect.name}", "min": 126 * keV, "max": 154 * keV},
    ]
    cc = gate_spect.add_digitizer_energy_windows(sim, crystal_name, channels)

    # arf actor for building the training dataset
    arf = sim.add_actor("ARFTrainingDatasetActor", "ARF (training)")
    arf.mother = detPlane.name
    arf.output = paths.output / "test043_arf_training_dataset.root"
    arf.energy_windows_actor = cc.name
    arf.russian_roulette = 100

    dpz = detPlane.translation[2]
    print(f"Position of the detector plane {dpz} mm")

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
    s.output = str(arf.output).replace(".root", "_stats.txt")

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("stats")
    print(stat)
    skip = gate.get_source_skipped_events(sim.output, "s1")
    print(f"Nb of skip particles {skip}  {(skip / stat.counts.event_count) * 100:.2f}%")

    # ----------------------------------------------------------------------------------------------------------------
    gate.warning("Compare stats")
    stats_ref = gate.read_stat_file(paths.output_ref / s.output)
    is_ok = gate.assert_stats(stat, stats_ref, 0.01)

    gate.warning("Compare root")
    checked_keys = [
        {"k1": "E", "k2": "E", "tol": 0.002, "scaling": 1},
        {"k1": "Theta", "k2": "Theta", "tol": 2, "scaling": 1},
        {"k1": "Phi", "k2": "Phi", "tol": 1.5, "scaling": 1},
        {"k1": "window", "k2": "window", "tol": 0.006, "scaling": 1},
    ]
    is_ok = (
        gate.compare_root2(
            paths.output_ref / "test043_arf_training_dataset.root",
            arf.output,
            "ARF (training)",
            "ARF (training)",
            checked_keys,
            paths.output / "test043_training_dataset.png",
            n_tol=14,
        )
        and is_ok
    )
