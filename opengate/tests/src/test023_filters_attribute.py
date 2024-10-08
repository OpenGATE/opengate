#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.random_seed = 321456987
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm
    sec = gate.g4_units.second
    keV = gate.g4_units.keV

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.type = "gauss"
    source.energy.mono = 1 * MeV
    source.energy.sigma_gauss = 1 * MeV
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.direction.type = "iso"
    source.activity = 1000 * Bq

    # plane
    plane1a = sim.add_volume("Box", "plane1a")
    plane1a.size = [1 * m, 1 * m, 1 * nm]
    plane1a.translation = [0, 0, 1 * cm]
    plane1a.material = "G4_AIR"
    plane1a.color = [1, 0, 0, 1]  # red

    plane1b = sim.add_volume("Box", "plane1b")
    plane1b.size = [1 * m, 1 * m, 1 * nm]
    plane1b.translation = [0, 0, 2 * cm]
    plane1b.material = "G4_AIR"
    plane1b.color = [1, 0, 0, 1]  # red

    plane2a = sim.add_volume("Box", "plane2a")
    plane2a.size = [1 * m, 1 * m, 1 * nm]
    plane2a.translation = [0, 0, -1 * cm]
    plane2a.material = "G4_AIR"
    plane2a.color = [0, 1, 0, 1]  # green

    plane2b = sim.add_volume("Box", "plane2b")
    plane2b.size = [1 * m, 1 * m, 1 * nm]
    plane2b.translation = [0, 0, -2 * cm]
    plane2b.material = "G4_AIR"
    plane2b.color = [0, 1, 0, 1]  # green

    # kill according to time
    ka = sim.add_actor("KillActor", "kill_actor1")
    ka.attached_to = plane1a.name
    att_filter = sim.add_filter("ThresholdAttributeFilter", "time_filter")
    # we don't kill the particle within the time range, so
    # we discard the kill filter when the time is in the correct range
    att_filter.attribute = "GlobalTime"
    att_filter.value_min = 20 * sec
    att_filter.value_max = 70 * sec
    att_filter.policy = "reject"
    print(att_filter)
    ka.filters.append(att_filter)

    # kill according to energy
    ka = sim.add_actor("KillActor", "kill_actor2")
    ka.attached_to = plane2a.name
    att_filter = sim.add_filter("ThresholdAttributeFilter", "ene_filter")
    att_filter.attribute = "KineticEnergy"
    att_filter.value_min = 300 * keV
    att_filter.value_max = 1200 * keV
    att_filter.policy = "accept"
    ka.filters.append(att_filter)

    # stats
    stat = sim.add_actor("SimulationStatisticsActor", "stats")
    stat.track_types_flag = True

    # phsp
    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp1")
    # warning, if the plane is plane1a the particle may be marked as "killed"
    # but will still be in the phsp
    phsp1.attached_to = plane1b.name
    phsp1.attributes = ["GlobalTime", "KineticEnergy"]
    phsp1.output_filename = f"test023_filters_attribute.root"
    phsp1.priority = ka.priority + 10

    # phsp
    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.attached_to = plane2b.name
    phsp2.attributes = ["GlobalTime", "KineticEnergy"]
    phsp2.output_filename = f"test023_filters_attribute.root"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    # start simulation
    duration = 100 * sec
    sim.run_timing_intervals = [[0, duration]]
    sim.run()

    # print results at the end
    print(stat)
    # reference :
    # stat.write(paths.output_ref / "test023_att_stats.txt")

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test023_att_stats.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.01)

    # image root files (no comparison here, just for plot)
    print()
    utility.compare_root3(
        phsp1.get_output_path(),
        phsp1.get_output_path(),
        "phsp1",
        "phsp2",
        keys1=phsp1.attributes,
        keys2=phsp1.attributes,
        tols=[1e20] * 2,
        scalings1=[1e-9, 1.0],
        scalings2=[1e-9, 1.0],
        img=paths.output / "test023_att.png",
        hits_tol=1e20,
    )

    # compare root files (no comparison here)
    print()
    is_ok = (
        utility.compare_root3(
            paths.output_ref / f"test023_filters_attribute.root",
            phsp1.get_output_path(),
            "phsp1",
            "phsp1",
            keys1=phsp1.attributes,
            keys2=phsp1.attributes,
            tols=[0.4, 0.02],
            scalings1=[1e-9, 1.0],
            scalings2=[1e-9, 1.0],
            img=paths.output / "test023_att_phsp1.png",
            hits_tol=2,
        )
        and is_ok
    )
    print()
    is_ok = (
        utility.compare_root3(
            paths.output_ref / f"test023_filters_attribute.root",
            phsp1.get_output_path(),
            "phsp2",
            "phsp2",
            keys1=phsp1.attributes,
            keys2=phsp1.attributes,
            tols=[0.6, 0.02],
            scalings1=[1e-9, 1.0],
            scalings2=[1e-9, 1.0],
            img=paths.output / "test023_att_phsp2.png",
            hits_tol=2,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
