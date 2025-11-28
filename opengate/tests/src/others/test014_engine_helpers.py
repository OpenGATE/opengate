#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


def define_simulation(sim, threads=1):
    um = gate.g4_units.um
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    keV = gate.g4_units.keV

    sim.running_verbose_level = gate.logger.RUN
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123654789
    sim.number_of_threads = threads
    print(sim)

    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    global_cut = 700 * um
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200000 / sim.number_of_threads

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True


def test_output(sim):
    # get output
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )

    stats = sim.get_actor("Stats")
    print(stats)
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)

    return is_ok
