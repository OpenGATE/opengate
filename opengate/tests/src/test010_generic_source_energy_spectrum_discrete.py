#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.sources.base import get_rad_gamma_spectrum
import numpy as np
import gatetools

import matplotlib.pyplot as plt


def plot(output_file, ekin, data_x, data_y, relerrs):
    bins = len(data_x)
    hist_y, hist_x = np.histogram(ekin, bins=bins)

    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.set_xlabel("Energy (MeV)")
    ax.set_ylabel("Number of particles")
    ax.scatter(data_x, data_y, label="input energy spectrum", marker="o")
    ax.scatter(
        data_x, hist_y, label="simulated energy spectrum", marker=".", linewidth=0.9
    )
    ax.legend()

    ax2 = ax.twinx()
    ax2.set_ylabel("Relative uncertainty")
    ax2.set_ylim([0, 0.05])
    ax2.plot(data_x, relerrs, label="relative uncertainty", linewidth=0.4)

    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def root_load_ekin(root_file: str):
    data_ref, keys_ref, m_ref = gatetools.phsp.load(root_file)

    index_ekin = keys_ref.index("KineticEnergy")
    ekin = [data_ref_i[index_ekin] for data_ref_i in data_ref]

    return ekin


def add_source_energy_spectrum_discrete(sim, phsp):
    spectrum = get_rad_gamma_spectrum("Lu177")

    source = sim.add_source("GenericSource", "beam")
    source.attached_to = phsp.name
    source.particle = "gamma"
    source.n = 5e5 / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum_discrete"
    source.energy.spectrum_energies = spectrum.energies
    source.energy.spectrum_weights = spectrum.weights

    return source


def run_simulation(paths):
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 987654321
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    g_cm3 = gate.g4_units.g_cm3

    # materials
    sim.volume_manager.material_database.add_material_weights(
        "Vacuum", ["H"], [1], 1e-12 * g_cm3
    )

    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "Vacuum"

    phsp = sim.add_volume("Sphere", "phsp")
    phsp.rmin = 0.1 * m
    phsp.rmax = 1 * m
    phsp.material = world.material

    source = add_source_energy_spectrum_discrete(sim, phsp)

    # actors
    phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp_actor")
    phsp_actor.output_filename = "test010_energy_spectrum_discrete.root"
    phsp_actor.attached_to = phsp.name
    phsp_actor.attributes = [
        "KineticEnergy",
    ]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # get info
    ekin = root_load_ekin(str(phsp_actor.get_output_path()))

    # test
    data_x = source.energy.spectrum_energies

    data_y = (
        np.array(source.energy.spectrum_weights)
        * source.n
        / np.sum(source.energy.spectrum_weights)
    )

    energy_counts = {}
    for energy in ekin:
        if energy not in energy_counts:
            energy_counts[energy] = 0
        energy_counts[energy] += 1

    output_y = [energy_counts[x] for x in data_x]

    relerrs = [abs(output_y[i] - data_y[i]) / data_y[i] for i in range(len(data_y))]
    oks = [
        utility.check_diff_abs(0, relerr, tolerance=0.05, txt="relative error")
        for relerr in relerrs
    ]
    is_ok = all(oks)

    plot(
        paths.output / "test010_plot_energy_spectrum_discrete.png",
        ekin,
        data_x,
        data_y,
        relerrs,
    )

    utility.test_ok(is_ok)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test010_generic_source_energy_spectrum", output_folder="test010"
    )

    run_simulation(paths)
