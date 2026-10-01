#!/usr/bin/env python3
"""Unequal run contributions must merge raw data before deriving AMDM ratios."""
import numpy as np
import opengate as gate
from opengate.actors.amdmoutput import ActorOutputAMDM
from opengate.tests import utility
from test110_amdm_helpers import (
    GAMMA, DELTA, output_dir, constant_lut, make_sim, arrays, check_outputs,
)


if __name__ == "__main__":
    directory = output_dir("multiple_runs")
    other_gamma = np.array([19., 3., 17.])
    other_delta = np.array([.8, .2, 0.])
    lut = constant_lut(directory, {6: (GAMMA, DELTA), 8: (other_gamma, other_delta)})
    sim, actor = make_sim(directory, lut=lut, primaries=[80, 0])
    first = sim.source_manager.sources["ions"]
    second = sim.add_source("GenericSource", "oxygen")
    second.particle = "ion 8 16"
    second.energy.mono = 60 * gate.g4_units.MeV
    second.number_of_primaries = [0, 240]
    second.position.type = first.position.type
    second.position.translation = list(first.position.translation)
    second.direction.type = first.direction.type
    second.direction.momentum = list(first.direction.momentum)
    second.weight = 1.0
    actor.user_output.amdm.keep_data_per_run = True
    sim.run_timing_intervals = [[0, 1], [1, 2]]
    sim.run(start_new_process=True)
    runs = [arrays(actor, i) for i in range(2)]
    merged = arrays(actor)
    for i, expected in enumerate([80, 240]):
        check_outputs(sim, actor, which=i, samples=expected)
        assert runs[i][0].sum() > 0
    check_outputs(sim, actor, samples=320)
    for component in range(3):
        np.testing.assert_allclose(merged[component], runs[0][component] + runs[1][component],
                                   rtol=1e-12, atol=1e-10)
    for i, (gamma, delta) in enumerate([(GAMMA, DELTA), (other_gamma, other_delta)]):
        mask = runs[i][0] > 0
        for b in range(3):
            np.testing.assert_allclose(runs[i][3][b][mask], delta[b], rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(runs[i][4][b][mask], gamma[b] if delta[b] else 0,
                                       rtol=1e-12, atol=1e-12)
    for numerator, denominator, derived in [(1, 0, 3), (2, 1, 4)]:
        expected = np.zeros_like(merged[numerator])
        np.divide(merged[numerator], merged[denominator], out=expected,
                  where=merged[denominator] != 0)
        np.testing.assert_allclose(merged[derived], expected, rtol=1e-12, atol=1e-12)
        wrong = (runs[0][derived] + runs[1][derived]) / 2
        assert not np.allclose(expected, wrong, rtol=1e-3, atol=1e-6), "case must detect ratio averaging"
    # The actor-output in-memory merge contract must retain the same raw-first rule.
    merged_output = ActorOutputAMDM(name="merged", belongs_to=actor, simulation=sim)
    merged_output.merge_data_from_actor_output(actor.user_output.amdm,
                                               actor.user_output.amdm)
    for item in [0, 1, 2]:
        np.testing.assert_allclose(merged_output.get_data(item=item), 2 * merged[item],
                                   rtol=1e-12, atol=1e-10)
    for item, index in [("delta", 3), ("gamma", 4)]:
        np.testing.assert_allclose(merged_output.get_data(item=item), merged[index],
                                   rtol=1e-12, atol=1e-12)
    print("Unequal runs, continued scoring and raw-first output merging passed")
    utility.test_ok(True)
