#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: stopping charged primaries.

A monoenergetic 1 MeV electron beam is fully absorbed in a 5 cm water cube.
Charge conservation gives a deposited charge close to -N, but not exactly:
a small fraction of primaries backscatter and a small fraction of secondary
delta electrons escape, both of which reduce |q|. The code checks that the
deposited charge is within 5% of -N.

Additional check: nominal and dynamic charges must agree exactly for leptons.
"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test0NN_deposited_charge"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 123456
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # For visual debugging: see the trajectories and
    # check how many of them leave the box
    # sim.visu = True
    # sim.visu_type = "qt"
    # sim.visu_commands.append("/vis/scene/endOfEventAction accumulate 10000")

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    target = sim.add_volume("Box", "target")
    target.size = [5 * cm, 5 * cm, 5 * cm]
    target.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

    n_events = 200
    source = sim.add_source("GenericSource", "electrons")
    source.particle = "e-"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = n_events

    charge = sim.add_actor("DepositedChargeActor", "charge")
    charge.attached_to = target.name

    charge_world = sim.add_actor("DepositedChargeActor", "charge_world")
    charge_world.attached_to = sim.world.name

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run()

    print(stats)
    print(charge)
    print(charge_world)

    expected = -float(n_events)
    got_nominal = charge.deposited_nominal_charge
    got_dynamic = charge.deposited_dynamic_charge

    expected_world = float(n_events)
    got_world = charge_world.deposited_nominal_charge

    tol = 0.05
    is_ok = True
    is_ok = (
        utility.print_test(
            abs(got_nominal - expected) / abs(expected) < tol,
            f"Nominal deposited charge: expected {expected}, got {got_nominal}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            got_nominal == got_dynamic,
            f"Nominal and dynamic must match exactly for leptons "
            f"(nominal={got_nominal}, dynamic={got_dynamic})",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            abs(got_world - expected_world) < tol * n_events,
            f"Deposited charge in world: expected {expected_world}, got {got_world}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
