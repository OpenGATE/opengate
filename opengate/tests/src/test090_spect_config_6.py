#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test090_helpers import *
from opengate import g4_units

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test090_spect_config_6"
    )

    data_path = paths.data

    # units
    deg = g4_units.deg
    Bq = g4_units.Bq
    cm = g4_units.cm
    mm = g4_units.mm
    sec = g4_units.s

    sc = SPECTConfig()
    sc.simu_name = "test090"
    sc.output_folder = paths.output
    sc.number_of_threads = 1
    # detectors
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.digitizer_channels = intevo.get_default_energy_windows("lu177")
    # phantom
    sc.phantom_config.image = data_path / "iec_5mm.mhd"
    sc.phantom_config.labels = data_path / "iec_5mm_labels.json"
    sc.phantom_config.material_db = data_path / "iec_5mm.db"
    # source
    sc.source_config.image = data_path / "iec_5mm_activity.mhd"
    sc.source_config.radionuclide = "177lu"
    sc.source_config.total_activity = 1e5 * Bq
    # acquisition
    sc.acquisition_config.radius = 300 * mm
    sc.acquisition_config.duration = 30 * sec
    sc.acquisition_config.number_of_angles = 3
    # ff
    sc.free_flight_config.angular_acceptance.max_rejection = 10000
    sc.free_flight_config.angular_acceptance.angle_tolerance_max = 15 * deg
    sc.free_flight_config.angular_acceptance.policy = "Rejection"
    sc.free_flight_config.angular_acceptance.skip_policy = "SkipEvents"
    sc.free_flight_config.angular_acceptance.enable_intersection_check = True
    sc.free_flight_config.angular_acceptance.enable_angle_check = True

    # create the simulation
    print(sc)
    sim = gate.Simulation()
    sc.setup_simulation(sim, visu=False)

    # write in a JSON file
    sc.to_json(paths.output / "spect_config.json")

    # read into another sc
    print()
    sc2 = SPECTConfig().from_json(paths.output / "spect_config.json")
    print(sc2)

    print()
    b = sc == sc2
    utility.print_test(b, "Test equality between write and read JSON files")
    is_ok = b

    sim = gate.Simulation()
    sc2.setup_simulation(sim, visu=False)
    b = sc == sc2
    utility.print_test(
        b, "Test equality between write and read JSON files (after setup)"
    )
    is_ok = b and is_ok

    utility.test_ok(is_ok)
