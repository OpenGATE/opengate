#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: neutral beam must deposit exactly zero charge.

A photon beam is fired through a vacuum box. The actor's early-return
after checking for neutral particles must avoid any accumulation,
so the result should be exactly zero, with no statistical fluctuation.

"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_neutral"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 42
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    target = sim.add_volume("Box", "target")
    target.size = [5 * cm, 5 * cm, 5 * cm]
    target.material = "G4_Galactic"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"

    n_events = 1000
    source = sim.add_source("GenericSource", "photons")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = n_events

    charge = sim.add_actor("DepositedChargeActor", "charge")
    charge.attached_to = target.name

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run()

    print(stats)
    print(charge)

    got_nominal = charge.deposited_nominal_charge
    got_dynamic = charge.deposited_dynamic_charge

    is_ok = True
    is_ok = (
        utility.print_test(
            got_nominal == 0.0,
            f"Neutral beam: nominal charge must be exactly 0.0, got {got_nominal}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            got_dynamic == 0.0,
            f"Neutral beam: dynamic charge must be exactly 0.0, got {got_dynamic}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
