#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from test077_scatter_helpers import *

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test077_scatter")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 1321654
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg
    MeV = gate.g4_units.MeV

    # world
    world = sim.world
    world.size = [5 * m, 5 * m, 5 * m]
    world.material = "G4_AIR"

    # waterbox
    wb = sim.add_volume("Box", "waterbox")
    wb.size = [20 * cm, 30 * cm, 30 * cm]
    wb.material = "G4_WATER"

    # detector
    det = sim.add_volume("Box", "detector")
    det.size = [10 * cm, 60 * cm, 60 * cm]
    det.translation = [40 * cm, 0, 0]
    det.material = "G4_WATER"
    det.material = "G4_Ir"

    # phys
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("waterbox", "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.type = "gauss"
    source.energy.mono = 0.5 * MeV
    source.energy.sigma_gauss = 0  # .2 * MeV
    source.position.type = "box"
    source.position.translation = [-60 * cm, 0, 0]
    source.position.size = [0 * cm, 8 * cm, 8 * cm]
    # source.direction.type = "focused"
    # source.direction.focus_point = [-20 * cm, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]
    source.n = 50000

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # phsp
    att_list = [
        "ParticleName",
        "ParentID",
        "PrePosition",
        "PostPosition",
        "EventKineticEnergy",
        "EventDirection",
        "EventID",
        "TrackID",
        "KineticEnergy",
        "PreDirection",
        "PostDirection",
        "UnscatteredPrimaryFlag",
    ]
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = det.name
    phsp.attributes = att_list
    # phsp.debug = True
    phsp.output_filename = "test077_scatter.root"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    f.policy = "accept"
    phsp.filters.append(f)

    # phsp
    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp_scatter")
    phsp2.attached_to = det.name
    phsp2.attributes = att_list
    phsp2.output_filename = phsp.output_filename
    # phsp2.debug = True
    fs = sim.add_filter("UnscatteredPrimaryFilter", "f_scatter")
    fs.policy = "accept"
    phsp2.filters.append(f)
    phsp2.filters.append(fs)

    # phsp
    phsp3 = sim.add_actor("PhaseSpaceActor", "phsp_no_scatter")
    phsp3.attached_to = det.name
    phsp3.attributes = att_list
    phsp3.output_filename = phsp.output_filename
    fs = sim.add_filter("UnscatteredPrimaryFilter", "f_no_scatter")
    fs.policy = "reject"
    phsp3.filters.append(f)
    phsp3.filters.append(fs)

    # start simulation
    sim.run()
    print(stats)

    # test
    print(phsp.get_output_path())
    print(phsp2.get_output_path())
    print(phsp3.get_output_path())
    is_ok = check_scatter(phsp.get_output_path())
    utility.test_ok(is_ok)
