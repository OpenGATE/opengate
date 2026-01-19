#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.userhooks import user_hook_active_regions, user_hook_em_switches
from opengate.tests import utility


def combined_user_hook_after_run(simulation_engine):
    user_hook_em_switches(simulation_engine)
    user_hook_active_regions(simulation_engine)


def check_hook_output(sim):
    # Check if G4 set flags correctly
    print(sim.user_hook_log[0])
    print(sim.user_hook_log[1])
    em_parameters_from_hook = sim.user_hook_log[0]
    for k, v in sim.physics_manager.em_parameters.items():
        assert v == em_parameters_from_hook[k]

    em_regions_from_hook = sim.user_hook_log[1]
    for r in sim.physics_manager.regions.values():
        assert r.em_switches.deex == em_regions_from_hook[r.name][0]
        assert r.em_switches.auger == em_regions_from_hook[r.name][1]
    assert (
        sim.physics_manager.em_switches_world.deex == em_regions_from_hook["world"][0]
    )
    assert (
        sim.physics_manager.em_switches_world.auger == em_regions_from_hook["world"][1]
    )


if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = True
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 1234

    # shortcuts for units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    # set the world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple waterbox volume
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"

    # add a daughter (in wb)
    b1 = sim.add_volume("Box", "b1")
    b1.mother = "waterbox"
    b1.size = [4 * cm, 4 * cm, 4 * cm]
    b1.translation = [5 * cm, 5 * cm, 0 * cm]
    b1.material = "G4_Pd"

    # add another box (in world)
    b2 = sim.add_volume("Box", "b2")
    b2.size = [4 * cm, 4 * cm, 4 * cm]
    b2.translation = [0 * cm, 0 * cm, 0 * cm]
    b2.material = "G4_LUNG_ICRP"

    # print info about physics
    print("Physics manager:\n", sim.physics_manager)
    print("Available phys lists:")
    print(sim.physics_manager.dump_available_physics_lists())

    source = sim.add_source("GenericSource", "gamma")
    source.particle = "gamma"
    source.energy.mono = 10 * MeV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 10 * Bq  # do not need high stats, testv just checks flags

    # change physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"

    # em parameters
    sim.physics_manager.em_parameters.fluo = True
    sim.physics_manager.em_parameters.auger = True
    sim.physics_manager.em_parameters.auger_cascade = True
    sim.physics_manager.em_parameters.pixe = True
    sim.physics_manager.em_parameters.deexcitation_ignore_cut = True

    # activate deex and auger in regions
    sim.physics_manager.em_switches_world.deex = True
    sim.physics_manager.em_switches_world.auger = True
    sim.physics_manager.em_switches_world.pixe = True

    region_b1 = sim.physics_manager.add_region("region_b1")
    region_b1.em_switches.deex = True
    region_b1.em_switches.auger = False
    region_b1.associate_volume(b1)

    region_b2 = sim.physics_manager.add_region("region_b2")
    region_b2.em_switches.deex = False
    region_b2.em_switches.auger = True
    region_b2.associate_volume(b2)

    sim.user_hook_after_run = combined_user_hook_after_run

    sim.run()
    check_hook_output(sim)

    utility.test_ok(True)
