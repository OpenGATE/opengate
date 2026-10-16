#!/usr/bin/env python3
"""FastY90Source validation, serialization and native voxel setup checks."""

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import itk
import numpy as np
import opengate_core as g4
from scipy.spatial.transform import Rotation

from opengate.managers import source_types
from opengate.sources.fasty90 import FastY90Source
from opengate.utility import g4_units


class NativeConfigRecorder:
    def InitializeUserInfo(self, user_info):
        self.user_info = user_info

    def SetTAC(self, times, activities):
        self.tac = (list(times), list(activities))


class FastY90ConfigTests(unittest.TestCase):
    def source(self, threads=1):
        simulation = SimpleNamespace(
            visu=False, multithreaded=threads > 1, number_of_threads=threads
        )
        return FastY90Source(name="y90", simulation=simulation)

    def test_defaults_and_registration(self):
        source = self.source()
        source.number_of_primaries = 100
        source.resolve_and_validate_config([[0, g4_units.s]])
        self.assertIs(source_types["FastY90Source"], FastY90Source)
        self.assertEqual(source.min_brem_energy, 0)
        self.assertEqual(source.positron_probability, 3.186e-5)
        self.assertIsNone(source.image)
        data = source.to_dictionary()
        self.assertEqual(data["object_type"], "FastY90Source")
        self.assertEqual(data["user_info"]["positron_probability"], 3.186e-5)

    def test_invalid_parameters(self):
        for name, value in [
            ("min_brem_energy", -0.01),
            ("min_brem_energy", 2),
            ("min_brem_energy", np.nan),
            ("min_brem_energy", np.inf),
            ("positron_probability", -0.1),
            ("positron_probability", 1.1),
            ("positron_probability", np.nan),
            ("positron_probability", np.inf),
        ]:
            with self.subTest(name=name, value=value):
                source = self.source()
                source.number_of_primaries = 10
                setattr(source, name, value)
                with self.assertRaisesRegex(Exception, name):
                    source.resolve_and_validate_config([[0, g4_units.s]])

    def test_incompatible_generic_options(self):
        for option in [
            "particle",
            "energy",
            "direction",
            "angular_acceptance",
            "polarization",
            "confine",
        ]:
            with self.subTest(option=option):
                source = self.source()
                source.number_of_primaries = 10
                if option == "particle":
                    source.particle = "e-"
                elif option == "energy":
                    source.energy.mono = 1
                elif option == "direction":
                    source.direction.type = "momentum"
                elif option == "angular_acceptance":
                    source.direction.angular_acceptance.policy = "Rejection"
                elif option == "polarization":
                    source.polarization = [1, 0, 0]
                else:
                    source.image = "activity.mhd"
                    source.position.confine = "phantom"
                with self.assertRaisesRegex(Exception, "FastY90Source"):
                    source.resolve_and_validate_config([[0, g4_units.s]])

    def test_thread_counts_are_partitioned_once(self):
        source = self.source(threads=3)
        source.number_of_primaries = [101, 10]
        intervals = [[0, g4_units.s], [g4_units.s, 2 * g4_units.s]]
        source.resolve_and_validate_config(intervals)
        workers = [NativeConfigRecorder() for _ in range(3)]
        source.g4_thread_sources = [NativeConfigRecorder(), *workers]
        for worker in workers:
            source.initialize_g4_source(worker, intervals)
        counts = np.array([w.user_info["number_of_primaries"] for w in workers])
        np.testing.assert_array_equal(counts.sum(axis=0), [101, 10])
        np.testing.assert_array_equal(source.number_of_primaries, [101, 10])

    def test_activity_and_tac_reach_native_source_as_decay_rates(self):
        source = self.source(threads=3)
        source.tac_times = [0, g4_units.s]
        source.tac_activities = [900 * g4_units.Bq, 300 * g4_units.Bq]
        source.half_life = 64 * g4_units.h
        source.min_brem_energy = 59 * g4_units.keV
        source.resolve_and_validate_config([[0, g4_units.s]])
        workers = [NativeConfigRecorder() for _ in range(3)]
        source.g4_thread_sources = [NativeConfigRecorder(), *workers]
        for worker in workers:
            source.initialize_g4_source(worker, [[0, g4_units.s]])
            self.assertAlmostEqual(worker.user_info["activity"], 300 * g4_units.Bq)
            np.testing.assert_allclose(
                worker.tac[1], np.array([300, 100]) * g4_units.Bq
            )
            self.assertEqual(worker.user_info["min_brem_energy"], 59 * g4_units.keV)
        self.assertAlmostEqual(source.activity, 900 * g4_units.Bq)

    def test_centered_voxel_grid_and_activity_weights(self):
        source = self.source()
        # Two voxels along x, with a 1:3 activity ratio.
        source._current_itk_image = itk.image_from_array(
            np.array([[[1, 3]]], dtype=np.float32)
        )
        source._current_itk_image.SetSpacing([2, 4, 6])
        source._current_itk_image.SetOrigin([100, 200, 300])
        source._current_itk_image.SetDirection(
            itk.matrix_from_array(
                Rotation.from_euler("z", 90, degrees=True).as_matrix()
            )
        )
        source.position.translation = [30, 40, 50]
        native = g4.GateVoxelSource()
        source.set_transform_from_user_info(native)
        source.cumulative_distribution_functions(native)
        distribution = native.GetSPSVoxelPosDistribution()
        # Image coordinates remain centered. Placement is applied by the native
        # FastY90Source once, when its run transformation is prepared.
        points = np.array([list(distribution.VGenerateOne()) for _ in range(10000)])
        self.assertTrue(np.all(np.abs(points) <= [2, 2, 3]))
        self.assertLess(abs(np.mean(points[:, 0] >= 0) - 0.75), 0.02)
        self.assertLess(abs(points[:, 0].mean() - 0.5), 0.05)

    def test_rejects_invalid_initial_and_replacement_images(self):
        for values in [
            np.zeros((1, 1, 2)),
            np.array([[[-1, 2]]]),
            np.array([[[np.nan, 1]]]),
            np.array([[[np.inf, 1]]]),
            np.ones((2, 2)),
        ]:
            with self.subTest(values=values):
                source = self.source()
                source._current_itk_image = itk.image_from_array(
                    values.astype(np.float32)
                )
                with self.assertRaisesRegex(Exception, "activity weights"):
                    source.cumulative_distribution_functions(g4.GateVoxelSource())
        source = self.source()
        source.g4_thread_sources = [g4.GateVoxelSource()]
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "invalid.mhd"
            itk.imwrite(
                itk.image_from_array(np.zeros((1, 1, 2), dtype=np.float32)),
                str(filename),
            )
            with self.assertRaisesRegex(Exception, "activity weights"):
                source.update_activity_image(filename)


if __name__ == "__main__":
    unittest.main()
