#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 6549

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 50 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 30000 * Bq

    # filter : keep e- only
    fp = sim.add_filter("ParticleFilter", "fp")
    fp.particle = "e-"

    # add dose actor
    dose1 = sim.add_actor("DoseActor", "dose1")
    dose1.output = paths.output / "test023-edep.mhd"
    # dose1.output = paths.output_ref / 'test023-edep.mhd'
    dose1.mother = "waterbox"
    dose1.size = [100, 100, 100]
    dose1.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose1.filters.append(fp)

    # add dose actor, without e- (to check)
    fe = sim.add_filter("ParticleFilter", "f")
    fe.particle = "e-"
    fe.policy = "discard"
    dose2 = sim.add_actor("DoseActor", "dose2")
    dose2.output = paths.output / "test023-noe-edep.mhd"
    # dose2.output = paths.output_ref / "test023-noe-edep.mhd"
    dose2.mother = "waterbox"
    dose2.size = [100, 100, 100]
    dose2.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose2.filters.append(fe)

    """fe = sim.add_filter("ParticleFilter", "f")
    fe.particle = "gamma"
    fe.policy = "discard"
    dose2.filters.append(fe)"""

    # add stat actor (only gamma)
    fg = sim.add_filter("ParticleFilter", "fp")
    fg.particle = "gamma"
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    s.filters.append(fg)

    print(s)
    print(dose1)
    print(dose2)
    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.global_production_cuts.all = 0.1 * mm

    # cuts = p.production_cuts
    # cuts.world.gamma = 0.1 * mm
    # cuts.world.proton = 0.1 * mm
    # cuts.world.electron = 0.1 * mm
    # cuts.world.positron = 0.1 * mm

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("Stats")
    print(stat)
    # stat.write(paths.output_ref / 'test023_stats.txt')

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test023_stats.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.8)

    print()
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023-edep.mhd",
        dose1.output,
        stat,
        tolerance=50,
        sum_tolerance=4,
    )

    print()
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023-noe-edep.mhd",
        dose2.output,
        stat,
        tolerance=40,
        sum_tolerance=2,
    )

    utility.test_ok(is_ok)
