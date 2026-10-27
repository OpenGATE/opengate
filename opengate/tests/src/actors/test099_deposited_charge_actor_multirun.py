#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: behaviour with multiple runs.

The simulation is split into two time runs. The actor scores each run
independently and, by default, accumulates a single merged result over all
runs. This test checks:

1. The merged result is the sum of the per-run results (charge, squared
   charge and number of events).
2. The merged number of events equals the total number of scored events.
3. With keep_data_per_run=True the per-run statistics are available with
   get_data(which=run_index).
"""

import numpy as np

import opengate as gate
from opengate.tests import utility


def create_sim(paths, keep_data_per_run):
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 654321
    sim.number_of_threads = 1
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    target = sim.add_volume("Box", "target")
    target.size = [5 * cm, 5 * cm, 5 * cm]
    target.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.apply_cuts = True

    n_events = 400
    source = sim.add_source("GenericSource", "electrons")
    source.particle = "e-"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # spread the events over 1 second, so that each run gets half of them
    source.activity = n_events * Bq
    sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1.0 * sec]]

    charge = sim.add_actor("DepositedChargeActor", "charge")
    charge.attached_to = target.name
    charge.user_output.charge.keep_data_per_run = keep_data_per_run

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    return sim, charge, stats


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_multirun"
    )

    is_ok = True

    # keep_data_per_run = True: per-run data available and consistent
    sim, charge, stats = create_sim(paths, keep_data_per_run=True)
    sim.run(start_new_process=True)
    print(charge)

    out = charge.user_output.charge
    merged = out.get_data(which="merged")
    run_indices = sorted(out.data_per_run.keys())

    is_ok = (
        utility.print_test(
            run_indices == [0, 1],
            f"Per-run data must be kept for both runs: got run indices {run_indices}",
        )
        and is_ok
    )

    per_run = [out.get_data(which=ri) for ri in run_indices]

    # print the per-run results next to the merged one
    print("Per-run deposited charge:")
    for ri in run_indices:
        nom = out.charge_statistics("nominal", which=ri)
        dyn = out.charge_statistics("dynamic", which=ri)
        print(
            f"  run {ri}: N={out.get_data(which=ri).number_of_events}, "
            f"nominal={nom['total']} +/- {nom['total_uncertainty']} e, "
            f"dynamic={dyn['total']} +/- {dyn['total_uncertainty']} e"
        )
    nom_m = out.nominal_charge_statistics
    dyn_m = out.dynamic_charge_statistics
    print(
        f"  merged: N={merged.number_of_events}, "
        f"nominal={nom_m['total']} +/- {nom_m['total_uncertainty']} e, "
        f"dynamic={dyn_m['total']} +/- {dyn_m['total_uncertainty']} e"
    )

    # every run must have scored some events (otherwise the test is trivial)
    is_ok = (
        utility.print_test(
            all(r.number_of_events > 0 for r in per_run),
            f"Each run must score events: " f"{[r.number_of_events for r in per_run]}",
        )
        and is_ok
    )

    # merged == sum over runs, for each accumulated quantity
    for key in merged.keys():
        run_sum = sum(r[key] for r in per_run)
        is_ok = (
            utility.print_test(
                np.isclose(merged[key], run_sum, rtol=1e-9, atol=1e-9),
                f"Merged '{key}' ({merged[key]}) must equal the sum over runs "
                f"({run_sum})",
            )
            and is_ok
        )

    # merged number of events must equal the total number of scored events
    total_events = stats.user_output.stats.merged_data.events
    is_ok = (
        utility.print_test(
            merged.number_of_events == total_events,
            f"Merged number_of_events ({merged.number_of_events}) must equal "
            f"the total scored events ({total_events})",
        )
        and is_ok
    )

    # per-run statistics must be retrievable and internally consistent
    stats_run0 = out.charge_statistics("nominal", which=0)
    is_ok = (
        utility.print_test(
            np.isclose(stats_run0["total"], per_run[0].deposited_nominal_charge),
            f"Per-run statistics total ({stats_run0['total']}) must match the "
            f"stored per-run charge ({per_run[0].deposited_nominal_charge})",
        )
        and is_ok
    )

    # default (keep_data_per_run = False): merged only, still correct
    sim2, charge2, stats2 = create_sim(paths, keep_data_per_run=False)
    sim2.run(start_new_process=True)

    out2 = charge2.user_output.charge
    is_ok = (
        utility.print_test(
            len(out2.data_per_run) == 0,
            f"With keep_data_per_run=False no per-run data must be kept "
            f"(got {len(out2.data_per_run)} runs)",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            out2.get_data(which="merged").number_of_events
            == stats2.user_output.stats.merged_data.events,
            "Merged result must remain correct even without per-run data",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
