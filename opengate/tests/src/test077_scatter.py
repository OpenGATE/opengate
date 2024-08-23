#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(
        __file__, output_folder="test077_scatter_order"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    # sim.random_seed = 12345678

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
    det.size = [1 * cm, 60 * cm, 60 * cm]
    det.translation = [40 * cm, 0, 0]
    det.material = "G4_WATER"

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
    source.direction.type = "focused"
    source.direction.focus_point = [-20 * cm, 0, 0]
    source.n = 1000

    # phsp
    att_list = [
        "ParticleName",
        "EventKineticEnergy",
        "EventDirection",
        "KineticEnergy",
        "PreDirection",
        "ScatterFlag",
    ]
    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp2.mother = det.name
    phsp2.attributes = att_list
    phsp2.output = paths.output / "test077_scatter.root"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp2.filters.append(f)

    # phsp
    phsp2 = sim.add_actor("PhaseSpaceActor", "phsp2")
    phsp2.mother = det.name
    phsp2.attributes = att_list
    phsp2.output = paths.output / "test077_scatter.root"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp2.filters.append(f)
    f = sim.add_filter("ScatterFilter", "f")
    f.policy = "keep_scatter"
    phsp2.filters.append(f)

    # phsp
    phsp3 = sim.add_actor("PhaseSpaceActor", "phsp3")
    phsp3.mother = det.name
    phsp3.attributes = att_list
    phsp3.output = paths.output / "test077_scatter.root"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp3.filters.append(f)
    f = sim.add_filter("ScatterFilter", "f")
    f.policy = "discard_scatter"
    phsp3.filters.append(f)

    # start simulation
    sim.run()

    # TODO: Test
    utility.test_ok(False)
