#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test090_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_1"
    )

    # TEST 1: intevo, Lu177, 2 heads, 3 angles

    # delete the output path content
    utility.delete_folder_contents(paths.output)
    data_path = paths.data
    mm = gate.g4_units.mm

    sc = SPECTConfig()
    sc.simu_name = "test090"
    sc.output_folder = paths.output
    sc.number_of_threads = 1
    # detectors
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.digitizer_function = intevo.add_digitizer
    sc.detector_config.size = [256, 256]
    sc.detector_config.spacing = [2.39759994 * mm, 2.39759994 * mm]
    # phantom
    sc.phantom_config.image = data_path / "iec_5mm.mhd"
    sc.phantom_config.labels = data_path / "iec_5mm_labels.json"
    sc.phantom_config.material_db = data_path / "iec_5mm.db"
    # source
    sc.source_config.image = data_path / "iec_5mm_activity.mhd"
    sc.source_config.radionuclide = "177lu"
    sc.source_config.total_activity = 5e4 * gate.g4_units.Bq
    # acquisition
    sc.acquisition_config.radius = 300 * gate.g4_units.mm
    sc.acquisition_config.duration = 30 * gate.g4_units.s
    sc.acquisition_config.number_of_angles = 3

    # create the simulation
    print(sc)
    sim = gate.Simulation()
    sc.setup_simulation(sim, visu=False)
    stats = sim.actor_manager.find_actors("stats")[0]

    # run it
    sim.random_seed = 987654
    sim.run()

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(272198, sc, stats, is_ok)
    is_ok = check_projection_files(sim, paths, stats, is_ok)

    utility.test_ok(is_ok)
