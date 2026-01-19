#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.contrib.spect.spect_config import *
from opengate.tests import utility

if __name__ == "__main__":

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test094_pytomography"
    )

    data_folder = paths.data
    output_folder = paths.output  # will be copied in the reference folder
    number_of_threads = 4

    # units
    deg = g4_units.deg
    cm = g4_units.cm
    mm = g4_units.mm
    Bq = g4_units.Bq

    # Init SPECT simulation
    sc = SPECTConfig()
    sc.output_folder = output_folder
    sc.number_of_threads = number_of_threads
    sc.detector_config.model = "intevo"
    sc.detector_config.collimator = "melp"
    sc.detector_config.number_of_heads = 2
    sc.detector_config.size = [128, 128]
    sc.detector_config.spacing = [4.8 * mm, 4.8 * mm]
    sc.detector_config.digitizer_function = intevo.add_digitizer
    sc.detector_config.digitizer_channels = get_default_energy_windows("lu177")
    sc.phantom_config.image = data_folder / "ct_5mm.mhd"
    sc.phantom_config.translation = [0, 0, -20 * g4_units.cm]
    sc.source_config.image = data_folder / "3_sources_5mm_v2.mhd"
    sc.source_config.radionuclide = "lu177"
    sc.acquisition_config.radius = 420 * g4_units.mm
    sc.acquisition_config.duration = 30 * g4_units.s
    sc.acquisition_config.number_of_angles = 30

    sc.free_flight_config.primary_activity = 1e6 * Bq
    sc.free_flight_config.scatter_activity = 2e6 * Bq
    sc.free_flight_config.angle_tolerance_max = 15 * deg
    sc.free_flight_config.forced_direction_flag = True
    sc.free_flight_config.angle_tolerance_min_distance = 6 * cm
    sc.free_flight_config.max_compton_level = 5
    sc.free_flight_config.compton_splitting_factor = 50
    sc.free_flight_config.rayleigh_splitting_factor = 50

    # debug
    # sc.free_flight_config.primary_activity = 5e1 * Bq
    # sc.free_flight_config.scatter_activity = 5e1 * Bq
    # sc.acquisition_config.number_of_angles = 1

    # run 1: primary
    sim = gate.Simulation()
    sc.setup_simulation_ff_primary_OLD(sim, visu=False)
    sim.run(start_new_process=True)
    stats = sim.find_actors("stats")[0]
    print(stats)

    # run 2: scatter
    print()
    sim = gate.Simulation()
    sc.setup_simulation_ff_scatter_OLD(sim, visu=False)
    sim.run(start_new_process=True)
    stats = sim.find_actors("stats")[0]
    print(stats)

    # combine and compute relative uncertainty
    n_prim = sc.free_flight_config.primary_activity / Bq
    n_scatter = sc.free_flight_config.scatter_activity / Bq
    n_ref = 1e8
    spect_freeflight_merge_all_heads(
        output_folder, n_prim, n_scatter, n_ref, nb_of_heads=2, verbose=True
    )
