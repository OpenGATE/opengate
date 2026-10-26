#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 129: the biasing actors can be restored from a dictionary.

A simulation is serialized with to_dictionary() and restored with
from_dictionary(), as done when a simulation is split into jobs. A biasing actor
must not hide one of its user infos (e.g. 'particles', 'processes') behind a
plain class attribute: the user info property is then lost and the restore fails.

For each biasing actor: the restore works and the user infos are the same, then
a simulation with the actor is split into jobs (without running them).
"""

import shutil

import opengate as gate
from opengate.tests import utility

ACTOR_TYPES = [
    "GammaFreeFlightActor",
    "ScatterSplittingFreeFlightActor",
    "BremsstrahlungSplittingActor",
    "LastVertexInteractionSplittingActor",
]


def create_simulation(actor_type):
    sim = gate.Simulation()
    sim.output_dir = paths.output / actor_type
    sim.run_timing_intervals = [
        [0, 1 * gate.g4_units.s],
        [1 * gate.g4_units.s, 2 * gate.g4_units.s],
    ]
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    source.activity = 100 * gate.g4_units.Bq
    actor = sim.add_actor(actor_type, "biasing")
    actor.attached_to = "world"
    return sim, actor


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test129")
    is_ok = True

    for actor_type in ACTOR_TYPES:
        print(f"\n----- {actor_type}")
        sim, actor = create_simulation(actor_type)

        # restore from the dictionary
        try:
            sim2 = gate.Simulation()
            sim2.from_dictionary(sim.to_dictionary())
            actor2 = sim2.actor_manager.get_actor("biasing")
            keys = [
                k
                for k in [
                    "particles",
                    "processes",
                    "exclude_volumes",
                    "splitting_factor",
                ]
                if k in actor.user_info
            ]
            same = all(actor2.user_info[k] == actor.user_info[k] for k in keys)
            is_ok = (
                utility.print_test(
                    same,
                    "Restored from dictionary, "
                    + ", ".join(f"{k}={actor2.user_info[k]}" for k in keys),
                )
                and is_ok
            )
        except Exception as e:
            is_ok = utility.print_test(False, f"Restore failed: {e}") and is_ok
            continue

        # split into jobs (the master simulation is cloned from the dictionary)
        campaign_dir = paths.output / actor_type / "campaign"
        shutil.rmtree(campaign_dir, ignore_errors=True)
        try:
            gate.jobs_split(simulation=sim, campaign_dir=campaign_dir, number_of_jobs=2)
            status = gate.jobs.jobs_status(campaign_dir)
            is_ok = (
                utility.print_test(
                    status["summary_counts"]["ready"] == 2, "Split into 2 jobs"
                )
                and is_ok
            )
        except Exception as e:
            is_ok = utility.print_test(False, f"Split failed: {e}") and is_ok

    utility.test_ok(is_ok)
