#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DepositedChargeActor: split-job merge.

The charge output participates in the jobs-merge protocol.
This test checks that a split run reproduces the non-split reference.

Setup is the one of test099_deposited_charge_actor.py: a 1 MeV
electron beam fully absorbed in a water cube, so the deposited charge is close
to -N with N the number of primaries.

What is checked:

1. A non-split reference run gives the expected charge and event count.
2. A 2-job split run merges into the same event count exactly, since the
   primaries are simply redistributed over the children.
3. The merged charge agrees with the reference within statistics.
4. The merged second moments are consistent, i.e. the uncertainty is finite
   and of the expected order. This is what actually uses load(), because
   the moments cannot be recovered from the derived statistics alone.
"""

import shutil

import opengate as gate
from opengate.tests import utility

N_EVENTS = 200
N_JOBS = 2


def make_simulation(output_dir, seed):
    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = seed
    sim.number_of_threads = 1
    sim.output_dir = output_dir

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

    source = sim.add_source("GenericSource", "electrons")
    source.particle = "e-"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -10 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = N_EVENTS

    charge = sim.add_actor("DepositedChargeActor", "charge")
    charge.attached_to = target.name
    # Persist the output: the jobs-merge workflow reloads each child
    # contribution from disk before merging it into the master output.
    # (Container-backed outputs are configured through the actor interface.)
    charge.charge.output_filename = "deposited_charge.json"

    sim.add_actor("SimulationStatisticsActor", "stats")
    return sim, charge


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test099_deposited_charge_jobs_merge"
    )
    shutil.rmtree(paths.output, ignore_errors=True)

    # --- 1. non-split reference ---
    sim_ref, charge_ref = make_simulation(paths.output / "reference", 123456)
    sim_ref.run()
    ref = charge_ref.user_output.charge.merged_data
    ref_nominal = ref.deposited_nominal_charge
    ref_events = ref.number_of_events
    print(f"reference: q={ref_nominal} e over N={ref_events} events")

    # --- 2. split run, merged from disk ---
    sim_split, charge_split = make_simulation(paths.output / "split", 123456)
    controller = sim_split.run(
        number_of_jobs=N_JOBS,
        wait_for_result=True,
        campaign_dir=paths.output / "split_campaign",
        split_policy="split_in_time_per_run",
        merge_after_run=True,
    )
    controller.merge_manager.print_merge_summary()

    merged = charge_split.user_output.charge.merged_data
    got_nominal = merged.deposited_nominal_charge
    got_events = merged.number_of_events
    got_sq = merged.deposited_nominal_charge_squared
    unc = charge_split.user_output.charge.nominal_charge_statistics["total_uncertainty"]
    print(f"split:     q={got_nominal} e over N={got_events} events")
    print(f"           sum of squares={got_sq}, total_uncertainty={unc}")

    is_ok = True

    is_ok = (
        utility.print_test(
            controller.stage == "merged",
            f"Split run reaches merged stage: {controller.stage}",
        )
        and is_ok
    )

    # The split redistributes the same primaries, so the event count is exact.
    is_ok = (
        utility.print_test(
            got_events == ref_events == N_EVENTS,
            f"Merged event count: expected {N_EVENTS}, "
            f"got {got_events} (reference {ref_events})",
        )
        and is_ok
    )

    # Charge is statistical across different child seeds; 5% is the same
    # tolerance used by the non-split test against the analytic expectation.
    is_ok = (
        utility.print_test(
            abs(got_nominal - ref_nominal) / abs(ref_nominal) < 0.05,
            f"Merged nominal charge: reference {ref_nominal}, got {got_nominal}",
        )
        and is_ok
    )

    # The second moments must survive the write/load round trip: each electron
    # contributes 0 or -1 per event, so the sum of squares is >= |q| and the
    # uncertainty must be finite and non-zero.
    is_ok = (
        utility.print_test(
            got_sq >= abs(got_nominal) > 0,
            f"Merged second moment survived the round trip: "
            f"sum of squares={got_sq} >= |q|={abs(got_nominal)}",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            0.0 < unc < abs(got_nominal),
            f"Merged uncertainty is finite and non-zero: {unc}",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
