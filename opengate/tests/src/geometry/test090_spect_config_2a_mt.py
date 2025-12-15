#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test090_helpers import *
from pathlib import Path

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_2_tc99m"
    )

    # TEST 2: nm670, tc99m, 1 head, 2 angles
    # ref = 5e6

    # delete the output path content
    utility.delete_folder_contents(paths.output)
    data_path = paths.data
    mm = gate.g4_units.mm

    sc = SPECTConfig()
    sc.simu_name = "test090"
    sc.output_folder = paths.output
    sc.number_of_threads = 4
    # detectors
    sc.detector_config.model = "nm670"
    sc.detector_config.collimator = "lehr"
    sc.detector_config.number_of_heads = 1
    # test default
    # sc.detector_config.digitizer_function = nm670.add_digitizer
    # sc.detector_config.digitizer_channels = get_default_energy_windows()
    sc.detector_config.size = [256 / 4, 256 / 4]
    sc.detector_config.spacing = [2.39759994 * mm * 4, 2.39759994 * mm * 4]
    # phantom
    sc.phantom_config.image = data_path / "iec_5mm.mhd"
    sc.phantom_config.labels = data_path / "iec_5mm_labels.json"
    sc.phantom_config.material_db = data_path / "iec_5mm.db"
    # source
    sc.source_config.image = data_path / "iec_5mm_activity.mhd"
    sc.source_config.radionuclide = "tc99m"
    sc.source_config.total_activity = 1e5 * gate.g4_units.Bq
    # sc.source_config.total_activity = 5e6 * gate.g4_units.Bq
    # acquisition
    sc.acquisition_config.radius = 300 * gate.g4_units.mm
    sc.acquisition_config.duration = 20 * gate.g4_units.s
    sc.acquisition_config.number_of_angles = 2

    # create the simulation
    print(sc)
    sim = gate.Simulation()
    sc.setup_simulation(sim, visu=False)
    stats = sim.actor_manager.find_actors("stats")[0]

    # run it
    sim.random_seed = 123456
    sim.run(start_new_process=True)

    # we check only that the output files exist
    is_ok = True
    is_ok = check_stats_file(1783357, sc, stats, is_ok, threads=sc.number_of_threads)
    is_ok = check_projection_files(
        sim,
        paths,
        stats,
        is_ok,
        tol=25,
        output_ref=Path(str(paths.output_ref) + "_ref"),
        scaling=50,
        axis="x",
        threads=sc.number_of_threads,
    )
    utility.test_ok(is_ok)
