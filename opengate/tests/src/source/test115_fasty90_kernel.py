#!/usr/bin/env python3
"""Check the installed kernel bindings against their compiled table distributions."""

import unittest

import numpy as np
import opengate_core as g4


class FastY90KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = g4.GateFastY90Kernel.GetTables()

    def sample(self, cutoff=0, positron_probability=3.186e-5, energy=0, p=None):
        if p is None:
            p = (np.arange(10001, dtype=float) + 0.5) / 10001
        kernel = g4.GateFastY90Kernel(cutoff, positron_probability)
        info = np.array(
            [
                kernel.GetBremsstrahlungYield(),
                kernel.GetTotalYield(),
                kernel.GetEffectiveMinBremEnergy(),
            ]
        )
        sampled = np.array(
            [
                [
                    kernel.IsPositron(probability),
                    kernel.SampleBremsstrahlungEnergy(probability, 0.37),
                    kernel.SamplePositronEnergy(probability),
                    kernel.SampleRange(energy, probability, 0.37),
                    kernel.SampleAngle(energy, probability, 0.37),
                ]
                for probability in p
            ],
            dtype=float,
        ).reshape(-1, 5)
        return info, sampled

    def test_default_parameters(self):
        kernel = g4.GateFastY90Kernel()
        total = self.tables["mEnergyTable"].sum()
        self.assertAlmostEqual(kernel.GetBremsstrahlungYield(), total)
        self.assertAlmostEqual(kernel.GetTotalYield(), total + 3.186e-5)
        self.assertEqual(kernel.GetEffectiveMinBremEnergy(), 0)
        kernel = g4.GateFastY90Kernel(min_brem_energy=0.059, positron_probability=0)
        self.assertEqual(kernel.GetEffectiveMinBremEnergy(), 0.05)
        self.assertEqual(kernel.GetTotalYield(), kernel.GetBremsstrahlungYield())

    def test_table_shapes_and_copies(self):
        shapes = {
            "mEnergyTable": (200,),
            "mRangeTable": (100, 120),
            "mAngleTable": (100, 180),
            "mPositronEnergyTable": (738,),
        }
        self.assertEqual(set(self.tables), set(shapes))
        copies = g4.GateFastY90Kernel.GetTables()
        for name, shape in shapes.items():
            with self.subTest(table=name):
                self.assertEqual(copies[name].shape, shape)
                self.assertEqual(copies[name].dtype, np.dtype(np.float64))
                copies[name].fill(-1)
        fresh = g4.GateFastY90Kernel.GetTables()
        for name in shapes:
            with self.subTest(table=name):
                np.testing.assert_array_equal(fresh[name], self.tables[name])

    def test_energy_cutoffs_yields_and_branch_ratio(self):
        p = (np.arange(10001, dtype=float) + 0.5) / 10001
        for cutoff in [0, 0.05, 0.059, 0.1, 1.98, 1.99, np.nextafter(2.0, 0)]:
            with self.subTest(cutoff=cutoff):
                info, sampled = self.sample(cutoff, 0.02, p=p)
                first = int(cutoff / 0.01)
                weights = self.tables["mEnergyTable"].copy()
                weights[:first] = 0
                cumulative = np.cumsum(weights)
                total = cumulative[-1]
                expected = (
                    np.searchsorted(cumulative / total, p, side="right") + 0.37
                ) * 0.01
                np.testing.assert_allclose(info, [total, total + 0.02, first * 0.01])
                np.testing.assert_allclose(sampled[:, 1], expected)
                np.testing.assert_array_equal(sampled[:, 0], p < 0.02 / (total + 0.02))

    def test_all_conditional_range_and_angle_distributions(self):
        p = (np.arange(1001, dtype=float) + 0.5) / 1001
        for row in range(100):
            with self.subTest(row=row):
                # Sample inside each 20 keV conditional-energy bin.
                _, sampled = self.sample(energy=(row + 0.5) * 0.02, p=p)
                for name, column, width in [
                    ("mRangeTable", 3, 0.1),
                    ("mAngleTable", 4, np.pi / 180),
                ]:
                    cdf = np.cumsum(self.tables[name][row])
                    bins = np.searchsorted(cdf / cdf[-1], p, side="right")
                    np.testing.assert_allclose(
                        sampled[:, column], (bins + 0.37) * width
                    )

    def test_positron_spectrum_and_disabled_branch(self):
        p = np.linspace(0, np.nextafter(1.0, 0), 10001)
        _, sampled = self.sample(positron_probability=0, p=p)
        self.assertTrue(np.all(sampled[:, 0] == 0))
        np.testing.assert_allclose(
            sampled[:, 2],
            np.searchsorted(self.tables["mPositronEnergyTable"], p, side="left")
            * 0.001,
        )

    def test_distribution_boundaries(self):
        # Empty cutoff bins must never be selected, including p == 0.
        p = np.array([0.0, np.nextafter(1.0, 0)])
        _, sampled = self.sample(cutoff=0.05, energy=2.0, p=p)
        self.assertTrue(np.all((sampled[:, 1] >= 0.05) & (sampled[:, 1] < 2)))
        self.assertTrue(np.all((sampled[:, 3] >= 0) & (sampled[:, 3] < 12)))
        self.assertTrue(np.all((sampled[:, 4] >= 0) & (sampled[:, 4] < np.pi)))

    def test_invalid_configuration(self):
        for cutoff, positron_probability in [
            (-0.01, 0),
            (2, 0),
            (np.nan, 0),
            (np.inf, 0),
            (0, -1),
            (0, 1.01),
            (0, np.nan),
            (0, np.inf),
        ]:
            with self.subTest(cutoff=cutoff, positron_probability=positron_probability):
                with self.assertRaises(ValueError):
                    g4.GateFastY90Kernel(cutoff, positron_probability)


if __name__ == "__main__":
    unittest.main()
