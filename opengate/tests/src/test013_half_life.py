#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test013_hl")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.check_volumes_overlap = False
    sim.output_dir = paths.output
    sim.random_seed = 42

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.s

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add two water boxes
    wb1 = sim.add_volume("Box", "waterbox1")
    wb1.size = [20 * cm, 20 * cm, 20 * cm]
    wb1.translation = [-20 * cm, 0, 0]
    wb2 = sim.add_volume("Box", "waterbox2")
    wb2.size = [20 * cm, 20 * cm, 20 * cm]
    wb2.translation = [20 * cm, 0, 0]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.global_production_cuts.all = 0.1 * mm
    # p.energy_range_min = 250 * eV
    # p.energy_range_max = 15 * MeV

    # sources info
    activity = 10 * Bq
    hl = 6586.26 * sec  # 109.771 minutes

    # source ion
    ion_src = sim.add_source("GenericSource", "ion_source")
    ion_src.mother = wb1.name
    ion_src.particle = "ion 9 18"  # F18
    ion_src.position.type = "sphere"
    ion_src.position.radius = 10 * mm
    ion_src.direction.type = "iso"
    ion_src.energy.type = "mono"
    ion_src.energy.mono = 0
    ion_src.half_life = hl
    ion_src.activity = activity

    # source e+
    beta_src = sim.add_source("GenericSource", "beta+_source")
    beta_src.mother = wb2.name
    beta_src.particle = "e+"
    beta_src.position.type = "sphere"
    beta_src.position.radius = 10 * mm
    beta_src.energy.type = "F18"
    beta_src.direction.type = "iso"
    beta_src.half_life = hl
    total_yield = gate.sources.generic.get_rad_yield("F18")
    print(f"{total_yield=}")
    beta_src.activity = activity * total_yield

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # filter for the phase space actor below
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "e+"

    # phsp
    phsp1 = sim.add_actor("PhaseSpaceActor", "phsp_ion")
    phsp1.attached_to = wb1.name
    phsp1.attributes = [
        "KineticEnergy",
        "LocalTime",
        "GlobalTime",
        "TrackProperTime",
        "TimeFromBeginOfEvent",
        # 'TrackVertexKineticEnergy', 'EventKineticEnergy'
    ]
    phsp1.output_filename = "test013_decay_ion.root"
    phsp1.steps_to_store = "first"
    phsp1.filters.append(f)

    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp_beta")
    phsp2.attached_to = wb2.name
    phsp2.attributes = phsp1.attributes
    phsp2.output_filename = "test013_decay_beta_plus.root"
    phsp2.filters.append(f)
    phsp2.steps_to_store = "first"

    # long run
    sim.run_timing_intervals = [[0, 109 * 60 * sec]]

    # start simulation
    sim.run()

    # print results
    print(stats)

    print()
    keys1 = phsp1.attributes
    keys2 = keys1
    scalings = [1] * len(keys1)
    scalings[2] = 1e-12  # GlobalTime
    tols = [0.02] * len(keys1)
    # tols[1] = 0.02  # LocalTime
    tols[2] = 0.06  # GlobalTime
    # tols[4] = 0.02  # TimeFromBeginOfEvent
    print(keys2, scalings, tols)
    print(phsp1.get_output_path())
    print(phsp2.get_output_path())
    print()
    is_ok = utility.compare_root3(
        phsp1.get_output_path(),
        phsp2.get_output_path(),
        "phsp_ion",
        "phsp_beta",
        keys1,
        keys2,
        tols,
        scalings,
        scalings,
        paths.output / "test013_decay.png",
    )

    utility.test_ok(is_ok)
