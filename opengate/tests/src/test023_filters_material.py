#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()
    sim.add_material_database(paths.data / "GateMaterials.db")

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 121645

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
    waterbox.material = "Water"
    waterbox.color = [0, 0, 1, 1]

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 50 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 30000 * Bq

    # filter : keep gamma
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    fp = sim.add_filter("ParticleFilter", "fp")
    fp.particle = "e-"

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test023-edep.mhd"
    # dose.output = paths.output_ref / "test023-edep.mhd"
    dose.mother = "waterbox"
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.filters.append(fp)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    s.filters.append(f)
    print(s)

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats2")
    s.track_types_flag = True
    s.filters.append(fp)
    print(s)

    print(dose)
    print("Filters: ", sim.filter_manager)
    print(sim.filter_manager.dump())

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.global_production_cuts.all = 0.1 * mm

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    stat = sim.output.get_actor("Stats")
    # print(stat)
    f = paths.output_ref / "test023_stats_iec_mat.txt"
    # stat.write(f)

    stat2 = sim.output.get_actor("Stats2")
    # print(stat2)
    f2 = paths.output_ref / "test023_stats_iec_mat_e.txt"
    # stat2.write(f2)

    # tests
    gate.exception.warning(f"Stats filter 1")
    stats_ref = utility.read_stat_file(f)
    is_ok = utility.assert_stats(stat, stats_ref, 0.07)

    print()
    gate.exception.warning(f"Stats filter 2")
    stats_ref = utility.read_stat_file(f2)
    is_ok = utility.assert_stats(stat2, stats_ref, 0.07) and is_ok

    is_ok = is_ok and utility.assert_images(
        paths.output_ref / "test023-edep.mhd",
        paths.output / "test023-edep.mhd",
        stat,
        sum_tolerance=3,
        tolerance=50,
    )

    utility.test_ok(is_ok)
