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
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 12332567
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

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
    dose.output_filename = "test023_iec_phantom.mhd"
    dose.attached_to = "iec"
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.filters = [fp, fk]

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    stat.filters.append(f)

    print(stat)
    print(dose)
    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.global_production_cuts.all = 0.1 * mm
    sim.user_hook_after_init = check_production_cuts

    # start simulation
    sim.run(start_new_process=True)

    # tests
    f = paths.output_ref / "test023_stats_iec_phantom.txt"
    stats_ref = utility.read_stat_file(f)
    is_ok = utility.assert_stats(stat, stats_ref, 0.12)
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023_iec_phantom.mhd",
        dose.edep.get_output_path(),
        stat,
        sum_tolerance=28,
        tolerance=102,
    )

    utility.test_ok(is_ok)
