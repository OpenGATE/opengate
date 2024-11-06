#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import numpy as np
import gatetools

import matplotlib.pyplot as plt


def plot(output_file, ekin, data_x, data_y, relerrs):
    bins = len(data_x)
    hist_y, hist_x = np.histogram(ekin, bins=bins)

    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.set_xlabel("Energy (MeV)")
    ax.set_ylabel("Number of particles")
    ax.plot(data_x, data_y, label="input energy spectrum", marker="o")
    ax.plot(
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


def add_source_energy_spectrum_histogram(sim, phsp, interpolation: str = None):
    spectrum = gate.sources.generic.get_ion_beta_spectrum("Lu177")

    source = sim.add_source("GenericSource", "beam")
    source.mother = phsp.name
    source.particle = "gamma"
    source.n = 5e5 / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"
    source.energy.type = "spectrum_histogram"
    source.energy.spectrum_energy_bin_edges = spectrum.energy_bin_edges
    source.energy.spectrum_weights = spectrum.weights
    source.energy.spectrum_histogram_interpolation = interpolation

    return source


def run_simulation(paths, interpolation: str = None):
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
    phsp.rmin = 0 * m
    phsp.rmax = 1 * m
    phsp.material = world.material

    source = add_source_energy_spectrum_histogram(sim, phsp, interpolation)

    # actors
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp_actor")
    phsp_actor.output_filename = (
        f"test010_energy_spectrum_histogram_{interpolation}.root"
    )
    # phsp_actor.attached_to = phsp
    phsp_actor.attributes = [
        "KineticEnergy",
    ]

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run(start_new_process=True)

    # get info
    ekin = root_load_ekin(str(phsp_actor.get_output_path()))

    # test
    bin_edges = source.energy.spectrum_energy_bin_edges
    data_x = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]

    data_y = (
        np.array(source.energy.spectrum_weights)
        * source.n
        / np.sum(source.energy.spectrum_weights)
    )

    bins = len(data_x)
    hist_y, hist_x = np.histogram(ekin, bins=bins)

    relerrs = [abs(hist_y[i] - data_y[i]) / data_y[i] for i in range(len(data_y))]
    oks = [
        utility.check_diff_abs(0, relerr, tolerance=0.05, txt="relative error")
        for relerr in relerrs
    ]
    is_ok = all(oks)

    plot(
        paths.output / f"test010_plot_energy_spectrum_histogram_{interpolation}.png",
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

    run_simulation(paths, interpolation=None)
    # run_simulation(paths, interpolation="linear")  # relative error ok until last values
