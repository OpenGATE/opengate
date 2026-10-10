#!/usr/bin/env python3
"""Python checks of the production raw reduction, independent of transport."""

import numpy as np
from opengate_core import opengate_core as g4
from opengate.tests import utility
from test103_AMF_calculator import expect_error


def accumulator(events):
    """Construct exact dyadic raw sums for selected synthetic event indices."""
    raw = g4._AMFRawAccumulator(3, [True] * 4, True)
    events = np.asarray(list(events))
    doses = (events % 4 + 1) * 0.25
    total = doses.sum()
    raw.dose = [total, 0, total]
    numerators = [
        np.sum(doses * (2 + events % 2)),
        total * 0.5,
        total * 0.125,
        total * 0.25,
    ]
    raw.moments = [[value, 0, value] for value in numerators]
    spectrum = total * np.arange(1, 401) * 0.125
    raw.spectra = np.concatenate([spectrum, np.zeros(400), spectrum]).tolist()
    return raw


def main():
    """Check worker count/order, beta mixing, empty voxels and lifecycle guards."""
    expected = accumulator(range(256))
    for count in (1, 2, 4, 8):
        for reverse in (False, True):
            workers = [accumulator(range(i, 256, count)) for i in range(count)]
            merged = accumulator([])
            for worker in reversed(workers) if reverse else workers:
                merged.merge(worker)
                assert worker.consumed
            for name in ("dose", "moments", "spectra"):
                np.testing.assert_array_equal(
                    getattr(merged, name), getattr(expected, name)
                )
            expect_error(lambda: merged.merge(workers[0]), "finalized or self")
            for worker in workers:
                worker.release()
                assert not worker.dose and not worker.spectra
            merged.finalize()
            assert merged.finalized
            np.testing.assert_array_equal(merged.dose, [160, 0, 160])
            np.testing.assert_array_equal(merged.moments[0], [2.6, 0, 2.6])
            np.testing.assert_array_equal(merged.moments[1], [0.5, 0, 0.5])
            np.testing.assert_array_equal(merged.moments[2], [0.125, 0, 0.125])
            np.testing.assert_array_equal(merged.moments[3], [0.0625, 0, 0.0625])
            np.testing.assert_array_equal(
                np.asarray(merged.spectra).reshape(3, 400)[1], 0
            )
            assert merged.spectra[399] == 50 and merged.spectra[-1] == 50
            expect_error(merged.finalize, "duplicate")
            expect_error(lambda: merged.merge(expected), "finalized or self")
    target = accumulator([])
    expect_error(lambda: target.merge(target), "finalized or self")
    expect_error(target.release, "active")
    expect_error(
        lambda: target.merge(g4._AMFRawAccumulator(1, [True] * 4, True)), "dimensions"
    )
    expect_error(
        lambda: target.merge(g4._AMFRawAccumulator(3, [False] * 4, True)), "outputs"
    )
    expect_error(lambda: g4._AMFRawAccumulator(0, [True] * 4, True), "dimensions")
    utility.test_ok(True)


if __name__ == "__main__":
    main()
