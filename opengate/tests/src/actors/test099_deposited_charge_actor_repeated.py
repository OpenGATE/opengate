#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: repeated volume placement.

Regression test for repeated placements:
    1) One actor attached to a single water box.
    2) One actor attached to repeated water slabs that form an equivalent box.

The two deposited charges should be close, because both geometries represent
the same amount of water traversed by the same beam setup.

A lead wall is placed between the two boxes to suppress particles crossing from
one box to the other.
"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_repeated"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 13579
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    # For visual debugging: see the trajectories and
    # check how many of them leave the box
    # sim.visu = True
    # sim.visu_type = "qt"
    # sim.visu_commands.append("/vis/scene/endOfEventAction accumulate 10000")

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    # Single monolithic volume
    single_box = sim.add_volume("Box", "single_box")
    single_box.size = [5 * cm, 5 * cm, 5 * cm]
    single_box.translation = [-8 * cm, 0, 0]
    single_box.material = "G4_WATER"

    # Repeated volumes: ten 5 mm slabs that form a 5 cm box.
    slab = sim.add_volume("Box", "slab")
    slab.size = [5 * cm, 5 * cm, 5 * mm]
    slab.translation = gate.geometry.utility.get_grid_repetition(
        [1, 1, 10], [0, 0, 5 * mm], start=[8 * cm, 0, -22.5 * mm]
    )
    slab.material = "G4_WATER"

    # Shield between the two targets to minimize secondary cross-talk.
    shield = sim.add_volume("Box", "shield")
    shield.size = [10 * cm, 20 * cm, 1 * m]
    shield.translation = [0, 0, 0]
    shield.material = "G4_Pb"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

    n_events = 1000

    source_single = sim.add_source("GenericSource", "electrons_single")
    source_single.particle = "e-"
    source_single.energy.mono = 1 * MeV
    source_single.position.type = "disc"
    source_single.position.radius = 1 * mm
    source_single.position.translation = [-8 * cm, 0, -10 * cm]
    source_single.direction.type = "momentum"
    source_single.direction.momentum = [0, 0, 1]
    source_single.n = n_events

    source_repeat = sim.add_source("GenericSource", "electrons_repeat")
    source_repeat.particle = "e-"
    source_repeat.energy.mono = 1 * MeV
    source_repeat.position.type = "disc"
    source_repeat.position.radius = 1 * mm
    source_repeat.position.translation = [8 * cm, 0, -10 * cm]
    source_repeat.direction.type = "momentum"
    source_repeat.direction.momentum = [0, 0, 1]
    source_repeat.n = n_events

    charge_single = sim.add_actor("DepositedChargeActor", "charge_single")
    charge_single.attached_to = single_box.name

    charge_repeat = sim.add_actor("DepositedChargeActor", "charge_repeat")
    charge_repeat.attached_to = slab.name

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run()

    print(stats)
    print(charge_single)
    print(charge_repeat)

    q_single_nom = charge_single.deposited_nominal_charge
    q_single_dyn = charge_single.deposited_dynamic_charge
    q_repeat_nom = charge_repeat.deposited_nominal_charge
    q_repeat_dyn = charge_repeat.deposited_dynamic_charge

    # Relative tolerance between equivalent geometries.
    tol_rel = 0.05
    rel_diff = abs(q_single_nom - q_repeat_nom) / max(abs(q_single_nom), 1.0)

    is_ok = True

    is_ok = (
        utility.print_test(
            rel_diff < tol_rel,
            f"Single box vs repeated slabs nominal charge must match within "
            f"{tol_rel*100:.0f}%: q_single={q_single_nom}, q_repeat={q_repeat_nom}, "
            f"relative diff={rel_diff:.4f}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            q_single_nom < 0 and q_repeat_nom < 0,
            f"Both charges must be negative for e- beam: "
            f"q_single={q_single_nom}, q_repeat={q_repeat_nom}",
        )
        and is_ok
    )

    is_ok = (
        utility.print_test(
            q_single_nom == q_single_dyn and q_repeat_nom == q_repeat_dyn,
            f"Nominal and dynamic must match exactly for leptons "
            f"(single: nominal={q_single_nom}, dynamic={q_single_dyn}; "
            f"repeat: nominal={q_repeat_nom}, dynamic={q_repeat_dyn})",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
