#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import numpy as np
import gatetools

import matplotlib.pyplot as plt


def root_load_ekin(root_file: str):
    data_ref, keys_ref, m_ref = gatetools.phsp.load(root_file)

    index_ekin = keys_ref.index("KineticEnergy")
    ekin = [data_ref_i[index_ekin] for data_ref_i in data_ref]

    return ekin


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_testX_energy_spectrum"
    )

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

    world = sim.world
    world.size = [10 * mm, 10 * mm, 10 * mm]
    world.material = "Vacuum"

    phsp = sim.add_volume("Sphere", "phsp")
    phsp.rmin = 4 * mm
    phsp.rmax = 5 * mm
    phsp.material = world.material

    spectrum_type = "histogram"
    spectrum_energy, spectrum_weight = gate.sources.generic.get_ion_energy_spectrum("Re186")

    source = sim.add_source("GenericSource", "beam")
    source.mother = phsp.name
    source.particle = "e-"
    source.n = 1e4 / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum"
    source.energy.spectrum_type = spectrum_type
    source.energy.spectrum_energy = spectrum_energy
    source.energy.spectrum_weight = spectrum_weight

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    phsp_actor = sim.add_actor("PhaseSpaceActor", f"phsp_actor_{spectrum_type}")
    phsp_actor.output_filename = f"testX-energy-spectrum-{spectrum_type}.root"
    phsp_actor.attach_to = phsp
    phsp_actor.attributes = [
        "KineticEnergy",
    ]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # get info
    print("Simulation seed:", sim.current_random_seed)
    print(stats)

    print("-" * 80)

    data_x = source.energy.spectrum_energy
    data_y = np.array(source.energy.spectrum_weight) * source.n

    bins = len(data_x)

    ekin = root_load_ekin(str(phsp_actor.get_output_path()))
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
