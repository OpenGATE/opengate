#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.sources.utility import set_source_energy_spectrum
import numpy as np
import gatetools

import matplotlib.pyplot as plt


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
    mm = gate.g4_units.mm
    g_cm3 = gate.g4_units.g_cm3

    # materials
    sim.volume_manager.material_database.add_material_weights(
        "Vacuum", ["H"], [1], 1e-12 * g_cm3
    )

    world = sim.world
    world.size = [10 * mm, 10 * mm, 10 * mm]
    world.material = "Vacuum"

    source = add_source_energy_spectrum_histogram(sim, interpolation)

    # actors
    # stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp_actor")
    phsp_actor.output_filename = (
        f"test010_energy_spectrum_histogram_{interpolation}.root"
    )
    phsp_actor.steps_to_store = "first"
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
    weights = source.energy.spectrum_weights

    src_data = np.array(weights)
    src_data = src_data / np.sum(src_data)

    sim_data, _ = np.histogram(ekin, bins=bin_edges, density=True)
    sim_data = sim_data / np.sum(sim_data)

    relerrs = (sim_data - src_data) / src_data
    oks = [
        utility.check_diff_abs(0, abs(relerrs[i]), tolerance=0.20, txt="relative error")
        for i in range(len(relerrs))
        if src_data[i] > 0.001
    ]
    is_ok = all(oks)

    plot(
        paths.output / f"test010_plot_energy_spectrum_histogram_{interpolation}.png",
        bin_edges,
        src_data,
        sim_data,
        relerrs,
    )

    utility.test_ok(is_ok)


def plot(output_file, bin_edges, src_data, sim_data, relerrs):
    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.set_xlabel("Energy (MeV)")
    ax.set_ylabel("Probability")
    ax.stairs(src_data, bin_edges, fill=True, label="input data")
    ax.stairs(sim_data, bin_edges, fill=True, alpha=0.6, label="simulation")

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax2 = ax.twinx()
    ax2.set_ylabel("Relative error")
    ax2.set_ylim([-0.20, +0.20])
    ax2.plot(
        (bin_edges[:-1] + bin_edges[1:]) / 2,
        relerrs,
        label="relative error",
        color="C2",
    )

    ax.legend()

    fig.savefig(output_file, dpi=300)
    plt.close(fig)


def root_load_ekin(root_file: str):
    data_ref, keys_ref, _ = gatetools.phsp.load(root_file)

    index_ekin = keys_ref.index("KineticEnergy")
    ekin = [data_ref_i[index_ekin] for data_ref_i in data_ref]

    return ekin


def add_source_energy_spectrum_histogram(sim, interpolation: str = None):
    source = sim.add_source("GenericSource", "beam")
    source.particle = "e-"
    source.n = 2e6 / sim.number_of_threads
    source.position.type = "point"
    source.direction.type = "iso"

    set_source_energy_spectrum(source, "Lu177")  # After defining the particle!!
    source.energy.spectrum_histogram_interpolation = interpolation

    return source


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "test010_generic_source_energy_spectrum", output_folder="test010"
    )

    run_simulation(paths, interpolation=None)
    # run_simulation(paths, interpolation="linear")  # relative error ok until last values
