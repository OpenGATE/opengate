#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import uproot
import sys
import math


def test022_half_life(n_threads=1):
    paths = utility.get_default_test_paths(__file__, output_folder="test022")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 12344321
    sim.output_dir = paths.output
    print(sim)

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s
    d = gate.g4_units.d

    # set the world size like in the Gate macro
    sim.world.size = [1 * m, 1 * m, 2 * m]

    # waterbox (not really used here)
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    waterbox.material = "G4_AIR"

    # detector
    detector = sim.add_volume("Box", "detector")
    detector.size = [80 * cm, 80 * cm, 1 * nm]
    detector.translation = [0, 0, 30 * cm]
    detector.material = "G4_BGO"
    detector.color = [1, 0, 0, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = (
        1 * mm
    )  # all means: protons, electrons, positrons, gammas

    # source #1
    source1 = sim.add_source("GenericSource", "source1")

    # source1.particle = "gamma"
    # spectrum = gate.sources.utility.get_spectrum("Lu177", "gamma", database="icrp107")
    # source1.energy.type = "spectrum_discrete"
    # source1.energy.spectrum_energies = spectrum.energies
    # source1.energy.spectrum_weights = spectrum.weights
    # source1.activity = 10 * Bq

    source1.particle = "ion 71 177"
    source1.activity = 0.1 * Bq
    source1.half_life = 6.647 * d
    # source1.user_particle_life_time = 6.647 * d / math.log(2.0)
    source1.user_particle_life_time = 0

    source1.position.type = "disc"
    source1.position.radius = 2 * cm
    source1.position.translation = [0, 0, -10 * cm]
    source1.direction.type = "focused"
    source1.direction.focus_point = [0, 0, 0]
    # source1.energy.mono = 100 * keV

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # hit actor
    ta = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta.attached_to = "detector"
    ta.attributes = ["KineticEnergy", "GlobalTime"]
    ta.output_filename = f"test022_half_lifev_{n_threads}.root"
    ta.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    f.policy = "accept"
    ta.filters.append(f)

    # timing
    sim.run_timing_intervals = [[0 * sec, 1e6 * sec]]
    # sim.run_timing_intervals = [[1e6 * sec, 2e6 * sec]]

    # start simulation
    sim.run(start_new_process=True)

    # get result
    print(stats)

    # read phsp
    with uproot.open(ta.get_output_path()) as root:
        branch = root["PhaseSpace"]["GlobalTime"]
        time = branch.array(library="numpy") / d

    # plot debug
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(5, 5))
    a = ax
    a.hist(
        time,
        bins=100,
        label="decay source",
        histtype="stepfilled",
        alpha=0.5,
        density=True,
    )
    a.legend()
    a.set_xlabel("time (d)")
    a.set_ylabel("detected photon")
    # plt.show()

    fn = paths.output / "test022_half_life_fit.png"
    print("Figure in ", fn)
    plt.savefig(fn)


def main():
    test022_half_life(n_threads=1)


if __name__ == "__main__":
    main()
