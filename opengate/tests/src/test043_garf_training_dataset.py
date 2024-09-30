#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import opengate as gate
import test043_garf_helpers as test43
from opengate.tests import utility
from opengate.tests.utility import print_test, test_ok

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test043_garf", "test043")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 1
    sim.visu = False
    sim.random_seed = 12365
    sim.output_dir = test43.paths.output

    # units
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV

    # activity
    activity = 1e6 * Bq / sim.number_of_threads

    # world size
    test43.sim_set_world(sim)

    # spect head
    spect, colli, cystal = gate_spect.add_spect_head(
        sim, "spect", collimator_type="lehr", debug=sim.visu
    )
    crystal_name = f"{spect.name}_crystal"

    # detector input plane
    pos, crystal_dist, psd = gate_spect.get_plane_position_and_distance_to_crystal(
        "lehr"
    )
    pos += 1 * nm  # to avoid overlap
    print(f"plane position     {pos / mm} mm")
    print(f"crystal distance   {crystal_dist / mm} mm")
    detPlane = test43.sim_add_detector_plane(sim, spect.name, pos)

    # physics
    test43.sim_phys(sim)

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
    arf.attached_to = detPlane.name
    arf.output_filename = "test043_arf_training_dataset.root"
    arf.energy_windows_actor = cc.name
    arf.russian_roulette = 100

    dpz = detPlane.translation[2]
    print(f"Position of the detector plane {dpz} mm")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "test043_arf_training_dataset_stats.txt"
    stats.stats.write_to_disk = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stats)

    # FIXME: will work once the source_manager will be refactored.
    skip = gate.sources.generic.get_source_skipped_events(sim, "s1")
    ref_skip = 615782
    is_ok = True
    if abs(skip - ref_skip) / ref_skip > 0.01:
        is_ok = False
    print_test(
        is_ok,
        f"Nb of skip particles {skip} (vs {ref_skip}) "
        f"{(skip / stats.counts.events) * 100:.2f}%",
    )

    # ----------------------------------------------------------------------------------------------------------------
    gate.exception.warning("Compare stats")
    stats_ref = utility.read_stat_file(
        paths.output_ref / "test043_arf_training_dataset_stats.txt"
    )
    is_ok = utility.assert_stats(stats, stats_ref, 0.01) and is_ok

    gate.exception.warning("Compare root")
    checked_keys = [
        {"k1": "E", "k2": "E", "tol": 0.002, "scaling": 1},
        {"k1": "Theta", "k2": "Theta", "tol": 2, "scaling": 1},
        {"k1": "Phi", "k2": "Phi", "tol": 1.5, "scaling": 1},
        {"k1": "window", "k2": "window", "tol": 0.006, "scaling": 1},
    ]
    is_ok = (
        utility.compare_root2(
            paths.output_ref / "test043_arf_training_dataset.root",
            arf.get_output_path(),
            "ARF (training)",
            "ARF (training)",
            checked_keys,
            paths.output / "test043_training_dataset.png",
            n_tol=14,
        )
        and is_ok
    )

    test_ok(is_ok)
