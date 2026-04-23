#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: stopping positrons must produce +N.

A 1 MeV positron beam into 5 cm of water: each positron enters,
slows down and annihilates inside. Expected deposited charge +N,
with the same small-fraction tolerance as the electron test to
account for backscatter + delta electrons escaping.

Additional check: the nominal and dynamic charge must match exactly, since the
lepton charge is fixed and cannot be modified by secondary processes.
"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_positrons"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 246810
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm

    # For visual debugging: see the trajectories and
    # check how many of them leave the box
    # sim.visu = True
    # sim.visu_type = "qt"
    # sim.visu_commands.append("/vis/scene/endOfEventAction accumulate 10000")

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    target = sim.add_volume("Box", "target")
    target.size = [5 * cm, 5 * cm, 5 * cm]
    target.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

    n_events = 20
    source = sim.add_source("GenericSource", "positrons")
    source.particle = "e+"
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

    expected = +float(n_events)
    got_nominal = charge.deposited_nominal_charge
    got_dynamic = charge.deposited_dynamic_charge

    tol = 0.05
    is_ok = True
    is_ok = (
        utility.print_test(
            got_nominal > 0,
            f"Positron beam must produce positive charge, got {got_nominal}",
        )
        and is_ok
    )
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

    utility.test_ok(is_ok)
