#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor — full traversal must produce near-zero charge.

Fires high-energy (200 MeV) protons at a thin (1 mm) water slab. The
CSDA range of 200 MeV protons in water is ~25 cm, so every primary
enters and exits. The deposited charge should be approximately 0.

A small nonzero residue is expected from: nuclear reactions and delta electrons.
A 2% tolerance (relative to n_primaries) accommodates this.

"""

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_traversal"
    )

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 987
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

    target = sim.add_volume("Box", "target")
    target.size = [10 * cm, 10 * cm, 1 * mm]
    target.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"

    n_events = 1000
    source = sim.add_source("GenericSource", "protons")
    source.particle = "proton"
    source.energy.mono = 200 * MeV
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

    tol = 0.02 * n_events  # absolute tolerance: 2% of primaries
    is_ok = True
    is_ok = (
        utility.print_test(
            abs(got_nominal) < tol,
            f"Traversal: nominal charge must be ~0 (|q| < {tol}), got {got_nominal}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            abs(got_dynamic) < tol,
            f"Traversal: dynamic charge must be ~0 (|q| < {tol}), got {got_dynamic}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
