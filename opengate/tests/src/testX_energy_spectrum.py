#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import numpy as np
import gatetools

import matplotlib.pyplot as plt


def get_ew_for(n: str):
    data = {
        "Co60": {
            "energy": [
                0.0000, 0.0746, 0.1491, 0.2237, 0.2982,
                0.3728, 0.4473, 0.5219, 0.5964, 0.6710,
                0.7455, 0.8201, 0.8947, 0.9692, 1.0438,
                1.1183, 1.1929, 1.2674, 1.3420, 1.4165,
            ],
            "weight": [
                4.45E-01, 3.30E-01, 1.78E-01, 4.58E-02, 6.36E-04,
                5.99E-05, 5.96E-05, 5.77E-05, 5.54E-05, 5.40E-05,
                5.23E-05, 4.99E-05, 4.66E-05, 4.24E-05, 3.71E-05,
                3.06E-05, 2.31E-05, 1.47E-05, 6.66E-06, 1.57E-06,
            ],
        },
        "Cu67": {
            "energy": [
                0.0000, 0.0287, 0.0575, 0.0862, 0.1150,
                0.1437, 0.1725, 0.2012, 0.2300, 0.2587,
                0.2875, 0.3162, 0.3450, 0.3737, 0.4025,
                0.4312, 0.4600, 0.4887, 0.5175, 0.5462,
            ],
            "weight": [
                1.25E-01, 1.20E-01, 1.16E-01, 1.09E-01, 1.00E-01,
                9.05E-02, 7.95E-02, 6.77E-02, 5.56E-02, 4.36E-02,
                3.23E-02, 2.24E-02, 1.46E-02, 9.60E-03, 6.28E-03,
                3.91E-03, 2.30E-03, 1.19E-03, 4.50E-04, 7.59E-05,
            ]
        },
        "Y90": {
            "energy": [
                0.0000, 0.1142, 0.2284, 0.3426, 0.4568,
                0.5710, 0.6852, 0.7994, 0.9136, 1.0278,
                1.1420, 1.2562, 1.3704, 1.4846, 1.5988,
                1.7130, 1.8272, 1.9414, 2.0556, 2.1698,
            ],
            "weight": [
                4.26E-02, 5.18E-02, 5.94E-02, 6.49E-02, 6.86E-02,
                7.08E-02, 7.17E-02, 7.15E-02, 7.04E-02, 6.85E-02,
                6.57E-02, 6.19E-02, 5.69E-02, 5.07E-02, 4.30E-02,
                3.42E-02, 2.46E-02, 1.50E-02, 6.43E-03, 1.13E-03,
            ],
        },
        "Ru106": {
            "energy": [
                0, 0.002, 0.0039, 0.0059, 0.0079,
                0.0098, 0.0118, 0.0138, 0.0158, 0.0177,
                0.0197, 0.0217, 0.0236, 0.0256, 0.0276,
                0.0295, 0.0315, 0.0335, 0.0355, 0.0374,
            ],
            "weight": [
                1.39E-01, 1.26E-01, 1.13E-01, 1.01E-01, 8.96E-02,
                7.89E-02, 6.89E-02, 5.95E-02, 5.07E-02, 4.25E-02,
                3.50E-02, 2.82E-02, 2.21E-02, 1.67E-02, 1.21E-02,
                8.13E-03, 4.99E-03, 2.53E-03, 9.93E-04, 1.78E-04,
            ],
        },
        "I131": {
            "energy": [
                0.0000, 0.0403, 0.0807, 0.1210, 0.1614,
                0.2017, 0.2421, 0.2824, 0.3227, 0.3631,
                0.4034, 0.4438, 0.4841, 0.5245, 0.5648,
                0.6052, 0.6455, 0.6858, 0.7262, 0.7665,
            ],
            "weight": [
                1.38E-01, 1.31E-01, 1.23E-01, 1.13E-01, 1.02E-01,
                8.94E-02, 7.70E-02, 6.47E-02, 5.30E-02, 4.15E-02,
                3.03E-02, 2.00E-02, 1.12E-02, 4.55E-03, 8.55E-04,
                1.15E-04, 6.94E-05, 4.13E-05, 1.73E-05, 2.96E-06,
            ],
        },
        "Sm153": {
            "energy": [
                0.0000, 0.0408, 0.0817, 0.1225, 0.1634,
                0.2042, 0.2451, 0.2859, 0.3268, 0.3676,
                0.4085, 0.4493, 0.4902, 0.5311, 0.5719,
                0.6127, 0.6536, 0.6945, 0.7353, 0.7761,
            ],
            "weight": [
                1.03E-01, 1.03E-01, 1.01E-01, 9.76E-02, 9.32E-02,
                8.74E-02, 8.04E-02, 7.24E-02, 6.35E-02, 5.41E-02,
                4.44E-02, 3.49E-02, 2.58E-02, 1.77E-02, 1.09E-02,
                6.02E-03, 2.92E-03, 1.27E-03, 4.86E-04, 7.24E-05,
            ],
        },
        "Ta175": {
            "energy": [
                0.0000, 0.0548, 0.1096, 0.1645, 0.2193,
                0.2741, 0.3289, 0.3838, 0.4386, 0.4934,
                0.5483, 0.6031, 0.6579, 0.7127, 0.7675,
                0.8224, 0.8772, 0.9320, 0.9869, 1.0417,
            ],
            "weight": [
                1.05E-05, 1.06E-04, 2.70E-04, 4.33E-04, 5.63E-04,
                6.48E-04, 6.86E-04, 6.82E-04, 6.40E-04, 5.68E-04,
                4.76E-04, 3.74E-04, 2.74E-04, 1.85E-04, 1.17E-04,
                7.37E-05, 4.29E-05, 2.03E-05, 7.36E-06, 1.26E-06,
            ],
        },
        "Lu177": {
            "energy": [
                0.0000, 0.0249, 0.0497, 0.0746, 0.0994,
                0.1243, 0.1491, 0.1740, 0.1988, 0.2237,
                0.2485, 0.2734, 0.2983, 0.3231, 0.3480,
                0.3728, 0.3977, 0.4225, 0.4474, 0.4722,
            ],
            "weight": [
                1.35E-01, 1.22E-01, 1.09E-01, 9.68E-02, 8.51E-02,
                7.45E-02, 6.57E-02, 5.88E-02, 5.22E-02, 4.56E-02,
                3.89E-02, 3.24E-02, 2.61E-02, 2.03E-02, 1.50E-02,
                1.05E-02, 6.64E-03, 3.46E-03, 1.48E-03, 2.97E-04,
            ],
        },
        "Re186": {
            "energy": [
                0.0269, 0.0807, 0.1346, 0.1884, 0.2422,
                0.2961, 0.3499, 0.4037, 0.4575, 0.5114,
                0.5652, 0.6190, 0.6728, 0.7266, 0.7805,
                0.8343, 0.8881, 0.9419, 0.9958, 1.0496,
            ],
            "weight": [
                7.50E-02, 7.80E-02, 7.98E-02, 8.03E-02, 7.94E-02,
                7.71E-02, 7.37E-02, 6.92E-02, 6.37E-02, 5.73E-02,
                5.03E-02, 4.28E-02, 3.52E-02, 2.77E-02, 2.06E-02,
                1.41E-02, 8.69E-03, 4.59E-03, 1.77E-03, 3.48E-04,
            ],
        },
    }

    return data[n]["energy"], data[n]["weight"]


def root_load_ekin(root_file: str):
    data_ref, keys_ref, m_ref = gatetools.phsp.load(root_file)

    index_ekin = keys_ref.index("KineticEnergy")
    ekin = [data_ref_i[index_ekin] for data_ref_i in data_ref]

    return ekin


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test010_generic_source_thetaphi"
    )

    print(paths.output_ref)

    # units
    mm = gate.g4_units.mm
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    deg = gate.g4_units.deg
    um = gate.g4_units.um
    g_cm3 = gate.g4_units.g_cm3

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123654

    # materials
    sim.volume_manager.material_database.add_material_weights(
        "Vacuum", ["H"], [1], 1e-9 * g_cm3
    )

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [10 * mm, 10 * mm, 10 * mm]
    world.material = "Vacuum"

    # add a simple volume
    phsp = sim.add_volume("Sphere", "phsp")
    phsp.rmin = 4 * mm
    phsp.rmax = 5 * mm
    phsp.material = "Vacuum"

    w, e = gate.sources.generic.get_rad_gamma_energy_spectrum("Tc99m")
    # test sources
    source = sim.add_source("GenericSource", "beam")
    source.particle = "e-"
    source.n = 1e6 / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum"
    source.energy.spectrum_type = "histogram"
    source.energy.spectrum_energy, source.energy.spectrum_weight = get_ew_for("Re186")
    # source.energy.spectrum_energy, source.energy.spectrum_weight = get_ew_for("I131")
    # source.energy.spectrum_energy, source.energy.spectrum_weight = get_ew_for("Co60")
    # source.energy.spectrum_energy, source.energy.spectrum_weight = get_ew_for("Ta175")

    # actors
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")

    phspActor = sim.add_actor("PhaseSpaceActor", "phspActor")
    phspActor.output = paths.output / "testX-energy-spectrum.root"
    phspActor.attach_to = "phsp"
    phspActor.attributes = [
        "KineticEnergy",
    ]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print
    print("Simulation seed:", sim.current_random_seed)

    # get results
    # stats.user_output.stats.store_data(?)

    print("-" * 80)

    data_x = source.energy.spectrum_energy
    data_y = np.array(source.energy.spectrum_weight) * source.n

    bins = len(data_x)

    ekin = root_load_ekin(phspActor.output)
    hist_y, hist_x = np.histogram(ekin, bins=bins)
    hist_x = [(hist_x[i] + hist_x[i+1]) / 2 for i in range(len(hist_x)-1)]

    plt.plot(data_x, data_y)
    plt.hist(ekin, bins=bins)
    plt.plot(data_x, hist_y)
    plt.plot(hist_x, hist_y)
    plt.show()

    relerrs = [abs(hist_y[i] - data_y[i]) / data_y[i] for i in range(len(data_y))]
    oks = [utility.check_diff_abs(0, relerr, tolerance=.15, txt="relative error") for relerr in relerrs]
    is_ok = all(oks)

    utility.test_ok(is_ok)
