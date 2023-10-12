#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.userhooks import check_production_cuts

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12332567

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # iec phantom
    iec_phantom = gate_iec.add_iec_phantom(sim)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 50 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 10000 * Bq

    # filter : keep gamma
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    fp = sim.add_filter("ParticleFilter", "fp")
    fp.particle = "e-"
    fk = sim.add_filter("KineticEnergyFilter", "fk")
    fk.energy_min = 100 * keV

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test023_iec_phantom.mhd"
    # dose.output = paths.output_ref / "test023_iec_phantom.mhd"
    dose.mother = "iec"
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.filters.append(fp)
    dose.filters.append(fk)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    s.filters.append(f)

    print(s)
    print(dose)
    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.global_production_cuts.all = 0.1 * mm
    sim.user_fct_after_init = check_production_cuts

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    stat = sim.output.get_actor("Stats")
    # stat.write(paths.output_ref / 'test023_stats_iec_phantom.txt')

    # tests
    f = paths.output_ref / "test023_stats_iec_phantom.txt"
    stats_ref = utility.read_stat_file(f)
    is_ok = utility.assert_stats(stat, stats_ref, 0.12)
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023_iec_phantom.mhd",
        paths.output / "test023_iec_phantom.mhd",
        stat,
        sum_tolerance=28,
        tolerance=102,
    )

    utility.test_ok(is_ok)
