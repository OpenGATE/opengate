#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: history-by-history uncertainty.

This test validates the uncertainty estimate two ways:

1. Internal consistency: for a single run the reported
   quantities must satisfy the relations
       total_uncertainty == sqrt(N) * std == N * sem
       relative_uncertainty == total_uncertainty / |total|

2. Batch cross-check: the per-run total_uncertainty is, by
   construction, an estimate of the run-to-run standard deviation of the total
   charge over independent simulations of the same size.
"""

import numpy as np

import opengate as gate
from opengate.tests import utility


def run_charge_sim(seed, n_events, paths):
    """Run one replica and return the DepositedChargeActor statistics."""
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = seed
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    target = sim.add_volume("Box", "target")
    target.size = [5 * cm, 5 * cm, 5 * cm]
    target.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

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

    sim.run(start_new_process=True)

    return {
        "n_events": charge.number_of_events,
        "nominal": charge.nominal_charge_statistics,
        "dynamic": charge.dynamic_charge_statistics,
    }


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_uncertainty"
    )

    n_events = 300
    n_replicas = 30
    base_seed = 42

    results = [
        run_charge_sim(base_seed + i, n_events, paths) for i in range(n_replicas)
    ]

    is_ok = True

    # 1. Internal consistency of the reported statistics
    r0 = results[0]
    n0 = r0["n_events"]
    nom = r0["nominal"]

    is_ok = (
        utility.print_test(
            n0 == n_events,
            f"Number of scored events must equal the number of primaries: "
            f"expected {n_events}, got {n0}",
        )
        and is_ok
    )

    u_from_std = np.sqrt(n0) * nom["std"]
    u_from_sem = n0 * nom["sem"]
    is_ok = (
        utility.print_test(
            np.isclose(nom["total_uncertainty"], u_from_std, rtol=1e-9, atol=1e-12)
            and np.isclose(nom["total_uncertainty"], u_from_sem, rtol=1e-9, atol=1e-12),
            f"total_uncertainty ({nom['total_uncertainty']}) must equal "
            f"sqrt(N)*std ({u_from_std}) and N*sem ({u_from_sem})",
        )
        and is_ok
    )

    # relative_uncertainty == total_uncertainty / |total|
    expected_rel = (
        nom["total_uncertainty"] / abs(nom["total"]) if nom["total"] != 0.0 else 0.0
    )
    is_ok = (
        utility.print_test(
            np.isclose(nom["relative_uncertainty"], expected_rel, rtol=1e-9),
            f"relative_uncertainty ({nom['relative_uncertainty']}) must equal "
            f"total_uncertainty/|total| ({expected_rel})",
        )
        and is_ok
    )

    # For a pure electron beam, nominal and dynamic must be identical.
    dyn = r0["dynamic"]
    is_ok = (
        utility.print_test(
            np.isclose(nom["total"], dyn["total"])
            and np.isclose(nom["total_uncertainty"], dyn["total_uncertainty"]),
            f"Nominal and dynamic statistics must match for electrons "
            f"(nominal total={nom['total']} +/- {nom['total_uncertainty']}, "
            f"dynamic total={dyn['total']} +/- {dyn['total_uncertainty']})",
        )
        and is_ok
    )

    # 2. Batch cross-check
    totals = np.array([r["nominal"]["total"] for r in results])
    reported_u = np.array([r["nominal"]["total_uncertainty"] for r in results])

    empirical_std = float(np.std(totals, ddof=1))  # batch-based uncertainty
    mean_reported_u = float(np.mean(reported_u))  # history-by-history estimate

    print(
        f"Total charge over {n_replicas} replicas of {n_events} events: "
        f"mean={np.mean(totals):.3f}, empirical std={empirical_std:.4f}"
    )
    print(
        f"History-by-history estimate: mean reported total_uncertainty="
        f"{mean_reported_u:.4f}"
    )

    is_ok = (
        utility.print_test(
            empirical_std > 0 and mean_reported_u > 0,
            f"Both uncertainties must be strictly positive "
            f"(empirical={empirical_std}, reported={mean_reported_u})",
        )
        and is_ok
    )

    tol = 0.25
    ratio = mean_reported_u / empirical_std
    is_ok = (
        utility.print_test(
            abs(ratio - 1.0) < tol,
            f"History-by-history uncertainty must match the batch estimate within "
            f"{tol*100:.0f}%: reported/empirical = {ratio:.3f}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
