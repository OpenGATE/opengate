#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor — multithreaded reduction correctness.

Runs the same setup as `test0NN_deposited_charge_actor.py`,
but with multithreading enabled.

Additionally checks taht:
  The per-primary charge matches -1.0 e within numerical tolerance.
"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test0NN_deposited_charge_mt"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 123456
    sim.number_of_threads = 4
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

    n_total = 2000
    source = sim.add_source("GenericSource", "electrons")
    source.particle = "e-"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = n_total // sim.number_of_threads  # n is per-thread

    charge = sim.add_actor("DepositedChargeActor", "charge")
    charge.attached_to = target.name

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run()

    print(stats)
    print(charge)

    events_simulated = stats.counts.events
    expected = -float(events_simulated)
    got_nominal = charge.deposited_nominal_charge
    got_dynamic = charge.deposited_dynamic_charge

    tol = 0.05
    is_ok = True

    is_ok = (
        utility.print_test(
            abs(got_nominal - expected) / abs(expected) < tol,
            f"MT nominal charge: expected {expected}, got {got_nominal} "
            f"(tolerance {tol*100:.0f}%)",
        )
        and is_ok
    )

    per_primary = got_nominal / events_simulated
    is_ok = (
        utility.print_test(
            abs(per_primary - (-1.0)) < tol,
            f"Per-primary charge: expected ≈ -1.0 e, got {per_primary:.4f}",
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
