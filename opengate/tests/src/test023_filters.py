#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 6549
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

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
    dose1.output_filename = "test023.mhd"
    dose1.attached_to = waterbox
    dose1.size = [100, 100, 100]
    dose1.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose1.filters.append(fp)

    # add dose actor, without e- (to check)
    fe = sim.add_filter("ParticleFilter", "fe")
    fe.particle = "e-"
    fe.policy = "reject"
    print(dir(fe))

    dose2 = sim.add_actor("DoseActor", "dose2")
    dose2.output_filename = "test023-noe.mhd"
    dose2.attached_to = waterbox
    dose2.size = [100, 100, 100]
    dose2.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose2.filters.append(fe)

    """fe = sim.add_filter("ParticleFilter", "f")
    fe.particle = "gamma"
    fe.policy = "reject"
    dose2.filters.append(fe)"""

    # add stat actor (only gamma)
    fg = sim.add_filter("ParticleFilter", "fg")
    fg.particle = "gamma"

    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    stat.filters.append(fg)

    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.global_production_cuts.all = 0.1 * mm

    # start simulation
    sim.run()

    # print results at the end
    print(stat)
    print(dose1)
    print(dose2)

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test023_stats.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.8)

    print()
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023-edep.mhd",
        dose1.edep.get_output_path(),
        stat,
        tolerance=50,
        sum_tolerance=4,
    )

    print()
    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023-noe-edep.mhd",
        dose2.edep.get_output_path(),
        stat,
        tolerance=40,
        sum_tolerance=2,
    )

    utility.test_ok(is_ok)
