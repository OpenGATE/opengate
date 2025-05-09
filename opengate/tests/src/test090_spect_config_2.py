#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.spect.ge_discovery_nm670 as nm670
from test090_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_2"
    )

    # TEST 2: nm670, tc99m, 1 head, 6 angles

    # delete the output path content
    utility.delete_folder_contents(paths.output)
    data_path = paths.data

    sc = SPECTConfig()
    sc.simu_name = "test090"
    sc.output_folder = paths.output
    # detectors
    sc.detector_config.model = "nm670"
    sc.detector_config.collimator = "lehr"
    sc.detector_config.number_of_heads = 1
    sc.detector_config.digitizer_function = nm670.add_digitizer_tc99m_v2
    # phantom
    sc.phantom_config.image = data_path / "iec_5mm.mhd"
    sc.phantom_config.labels = data_path / "iec_5mm_labels.json"
    sc.phantom_config.material_db = data_path / "iec_5mm.db"
    # source
    sc.source_config.image = data_path / "iec_5mm_activity.mhd"
    sc.source_config.radionuclide = "tc99m"
    sc.source_config.total_activity = 5e3 * gate.g4_units.Bq
    # acquisition
    sc.acquisition_config.radius = 300 * gate.g4_units.mm
    sc.acquisition_config.duration = 20 * gate.g4_units.s
    sc.acquisition_config.number_of_angles = 2

    # create the simulation
    print(sc)
    sim = gate.Simulation()
    output = sc.create_simulation(sim, number_of_threads=1, visu=False)
    print(output)

    # run it
    sim.random_seed = 123456
    sim.run(start_new_process=True)

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(88707, sc, output, is_ok)
    # is_ok = check_projection_files(sim, paths, output, is_ok)

    # run it again
    sc.acquisition_config.number_of_angles = 3
    sc.source_config.radionuclide = "in111"
    sim = gate.Simulation()
    output = sc.create_simulation(sim, number_of_threads=1, visu=False)
    sim.random_seed = 987654
    sim.run(start_new_process=True)

    # test
    is_ok = check_stats_file(184028, sc, output, is_ok)
    is_ok = check_projection_files(sim, paths, output, is_ok, tol=70)
    utility.test_ok(is_ok)
