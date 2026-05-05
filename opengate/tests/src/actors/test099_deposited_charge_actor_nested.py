#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: nested volumes.

A 1 MeV electron beam is aimed at a nested geometry composed of outer
`G4_Galactic` containers (including `mother1` and `daughter13`) and an
innermost `G4_WATER` target volume (`daughter131`). Actors are attached to
nested volumes to verify that deposited charge is partitioned according to
the actual region where transport occurs.

Purpose:
  Verify partition semantics with nested volumes.
  Crossing an inner interface must be counted as exiting one region and
  entering the next, with charge assigned to the corresponding attached actor.

Expected behavior:
  - Volumes filled with `G4_Galactic` should contribute no deposited charge.
  - The innermost water volume should collect the primary deposited charge,
    since the electrons stop in water.
  - The nested actors should therefore reflect the implemented geometry rather
    than a mother/daughter water-only configuration.
"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_nested"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 42
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

    mother1 = sim.add_volume("Box", "mother1")
    mother1.size = [5 * cm, 5 * cm, 5 * cm]
    mother1.translation = [0, 0, 0 * cm]
    mother1.material = "G4_Galactic"

    daughter11 = sim.add_volume("Box", "daughter11")
    daughter11.mother = mother1.name
    daughter11.size = [1 * cm, 1 * cm, 1 * cm]
    daughter11.material = "G4_Galactic"
    daughter11.translation = [0, 0, 2 * cm]

    daughter12 = sim.add_volume("Box", "daughter12")
    daughter12.mother = mother1.name
    daughter12.size = [1 * cm, 1 * cm, 1 * cm]
    daughter12.material = "G4_Galactic"
    daughter12.translation = [0, 0, -2 * cm]

    daughter13 = sim.add_volume("Box", "daughter13")
    daughter13.mother = mother1.name
    daughter13.size = [2 * cm, 2 * cm, 2 * cm]
    daughter13.material = "G4_Galactic"
    daughter13.translation = [0, 0, 0]

    daughter131 = sim.add_volume("Box", "daughter131")
    daughter131.mother = daughter13.name
    daughter131.size = [1 * cm, 1 * cm, 1 * cm]
    daughter131.material = "G4_WATER"
    daughter131.translation = [0, 0, 0]

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

    n_events = 200
    source = sim.add_source("GenericSource", "electrons")
    source.particle = "e-"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -50 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = n_events

    charge_mother1 = sim.add_actor("DepositedChargeActor", "charge_mother1")
    charge_mother1.attached_to = mother1.name

    charge_daughter11 = sim.add_actor("DepositedChargeActor", "charge_daughter11")
    charge_daughter11.attached_to = daughter11.name

    charge_daughter12 = sim.add_actor("DepositedChargeActor", "charge_daughter12")
    charge_daughter12.attached_to = daughter12.name

    charge_daughter13 = sim.add_actor("DepositedChargeActor", "charge_daughter13")
    charge_daughter13.attached_to = daughter13.name

    charge_daughter131 = sim.add_actor("DepositedChargeActor", "charge_daughter131")
    charge_daughter131.attached_to = daughter131.name

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run()

    print(stats)
    print(charge_mother1)
    print(charge_daughter11)
    print(charge_daughter12)
    print(charge_daughter13)
    print(charge_daughter131)

    expected_total = -float(n_events)

    q_mother1 = charge_mother1.deposited_nominal_charge
    q_daughter11 = charge_daughter11.deposited_nominal_charge
    q_daughter12 = charge_daughter12.deposited_nominal_charge
    q_daughter13 = charge_daughter13.deposited_nominal_charge
    q_daughter131 = charge_daughter131.deposited_nominal_charge

    expected_mother1 = 0
    expected_daughter11 = 0
    expected_daughter12 = 0
    expected_daughter13 = 0
    expected_daughter131 = -float(n_events)

    tol = 0.05
    is_ok = True

    is_ok = (
        utility.print_test(
            abs(q_mother1 - expected_mother1) <= tol * n_events,
            f"Mother1 charge: expected {expected_mother1}, got {q_mother1}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            abs(q_daughter11 - expected_daughter11) < tol * n_events,
            f"Daughter11 charge: expected {expected_daughter11}, got {q_daughter11}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            abs(q_daughter12 - expected_daughter12) <= tol * n_events,
            f"Daughter12 charge: expected {expected_daughter12}, got {q_daughter12}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            abs(q_daughter13 - expected_daughter13) <= tol * n_events,
            f"Daughter13 charge: expected {expected_daughter13}, got {q_daughter13}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            abs(q_daughter131 - expected_daughter131) <= tol * n_events,
            f"Daughter131 charge: expected {expected_daughter131}, got {q_daughter131}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            abs(
                (q_mother1 + q_daughter11 + q_daughter12 + q_daughter13 + q_daughter131)
                - expected_total
            )
            / abs(expected_total)
            < tol,
            f"Mother + daughters should be close to {expected_total} "
            f"(total={q_mother1 + q_daughter11 + q_daughter12 + q_daughter13 + q_daughter131}, "
            f"mother1={q_mother1}, daughter11={q_daughter11}, daughter12={q_daughter12}, "
            f"daughter13={q_daughter13}, daughter131={q_daughter131})",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
