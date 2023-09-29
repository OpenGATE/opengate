#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


def define_simulation(sim, threads=1):
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq

    ui = sim.user_info
    ui.running_verbose_level = gate.logger.RUN
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_engine = "MersenneTwister"
    ui.random_seed = 123654789
    ui.number_of_threads = threads
    print(ui)

    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    um = gate.g4_units.um
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
    source.n = 200000 / ui.number_of_threads

    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True


def test_output(output):
    # get output
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )

    stats = output.get_actor("Stats")
    print(stats)
    ui = output.simulation.user_info
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    stats_ref.counts.run_count = ui.number_of_threads
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.01)

    return is_ok
