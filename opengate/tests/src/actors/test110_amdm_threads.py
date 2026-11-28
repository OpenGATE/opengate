#!/usr/bin/env python3
"""Scientifically relevant ST/MT aggregates and exact constant-bin identities."""

import numpy as np
from opengate.tests import utility
from test110_amdm_helpers import (
    output_dir,
    make_sim,
    assert_constant_scoring,
    check_outputs,
)

if __name__ == "__main__":
    totals = []
    for threads in [1, 2]:
        sim, actor = make_sim(
            output_dir(f"threads_{threads}"), threads=threads, primaries=400
        )
        sim.run(start_new_process=True)
        totals.append(assert_constant_scoring(actor))
        check_outputs(sim, actor, samples=400)
    # Different thread scheduling uses different random streams. The small fully
    # contained beam has almost deterministic total deposition; 2% allows its
    # transport fluctuations while exposing lost/raced updates or duplicated events.
    np.testing.assert_allclose(totals[1], totals[0], rtol=0.02, atol=0)
    print("ST/MT weighted energy totals", totals)
    utility.test_ok(True)
