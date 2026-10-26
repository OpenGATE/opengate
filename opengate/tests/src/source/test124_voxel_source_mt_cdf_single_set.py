#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for https://github.com/OpenGATE/opengate/issues/1163

A multithreaded run with a VoxelSource must set the (expensive) cumulative
distribution function into each thread-local C++ source exactly once, on the
main thread. Before the fix, every Geant4 worker thread re-applied the CDF in
its own Build() callback, which copies the whole CDF while holding the GIL.
For large activity images this serialised the workers and starved the Python
physics constructor (UserLimitsPhysics), so G4MTRunManager::Initialize()
appeared to hang when the worker count grew.

The assertion is deterministic (no stochastic tolerance): the C++ setter is
called exactly 1 + number_of_threads times, i.e. once per pre-created
thread-local source. A regression that re-introduces the per-worker call makes
this count larger and fails the test.

Statistics: 200 histories, seed 123456 (the assertion does not depend on them).

Also checks the CDFs given to the C++ side (flat arrays, see #1155): the values
of compute_image_3D_CDF are the same as with the former (loop) version, and
the C++ setter refuses arrays with inconsistent shapes.
"""

import numpy as np
import itk

import opengate as gate
from opengate.tests import utility
import opengate_core as g4


def reference_3D_CDF(array):
    """The former (loop) version of compute_image_3D_CDF, as reference."""
    array = array / np.sum(array)
    sumx = np.sum(array, axis=2)
    sumxy = np.sum(sumx, axis=1)
    cdf_x = []
    for i in range(array.shape[0]):
        cdf_x.append([])
        for j in range(array.shape[1]):
            t = np.cumsum(array[i][j])
            if t[-1] != 0:
                t = t / t[-1]
            cdf_x[i].append(t)
    cdf_y = []
    for i in range(len(sumx)):
        t = np.cumsum(sumx[i])
        if t[-1] != 0:
            t = t / t[-1]
        cdf_y.append(t)
    cdf_z = np.cumsum(sumxy) / np.sum(sumxy)
    return np.array(cdf_x), np.array(cdf_y), cdf_z


def check_cdf():
    is_ok = True
    # random activity, with empty rows and planes (zero CDFs)
    rng = np.random.default_rng(42)
    arr = rng.random((7, 5, 6))
    arr[2] = 0
    arr[4, 1] = 0
    img = itk.image_from_array(arr.astype(np.float32))
    cdf_x, cdf_y, cdf_z = gate.image.compute_image_3D_CDF(img)
    ref_x, ref_y, ref_z = reference_3D_CDF(arr.astype(np.float32).astype(np.float64))
    b = (
        cdf_x.shape == (7, 5, 6)
        and cdf_y.shape == (7, 5)
        and cdf_z.shape == (7,)
        and cdf_x.dtype == np.float64
        and np.allclose(cdf_x, ref_x, rtol=0, atol=1e-12)
        and np.allclose(cdf_y, ref_y, rtol=0, atol=1e-12)
        and np.allclose(cdf_z, ref_z, rtol=0, atol=1e-12)
    )
    utility.print_test(b, "CDFs: same values as the former loop version")
    is_ok = is_ok and b

    # inconsistent shapes are refused by the C++ setter
    pg = g4.GateSPSVoxelsPosDistribution()
    for name, args in [
        ("cdf_y with a wrong nz", (cdf_z, cdf_y[:-1], cdf_x)),
        ("cdf_x with a wrong ny", (cdf_z, cdf_y, cdf_x[:, :-1])),
        ("cdf_x as 2D", (cdf_z, cdf_y, cdf_y)),
        ("empty", (cdf_z[:0], cdf_y[:0], cdf_x[:0])),
    ]:
        try:
            pg.SetCumulativeDistributionFunction(*args)
            b = False
        except ValueError:
            b = True
        utility.print_test(b, f"CDFs refused: {name}")
        is_ok = is_ok and b
    pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)
    return is_ok


def main():
    cdf_ok = check_cdf()
    paths = utility.get_default_test_paths(__file__, output_folder="test124_mt")

    number_of_threads = 4

    # Count the calls to the C++ CDF setter. It is the expensive operation
    # (it copies all three CDFs) and the one that must run only on the main
    # thread, once per thread-local source.
    real_setter = g4.GateSPSVoxelsPosDistribution.SetCumulativeDistributionFunction
    calls = {"count": 0}

    def counting_setter(self, vz, vy, vx):
        calls["count"] += 1
        return real_setter(self, vz, vy, vx)

    g4.GateSPSVoxelsPosDistribution.SetCumulativeDistributionFunction = counting_setter

    try:
        sim = gate.Simulation()
        sim.number_of_threads = number_of_threads
        sim.random_seed = 123456
        sim.output_dir = paths.output
        sim.run_timing_intervals = [[0, 1 * gate.g4_units.s]]

        mm = gate.g4_units.mm
        MeV = gate.g4_units.MeV

        # small activity image; the assertion is about the *number* of CDF
        # setter calls, not about the image size
        shape = (20, 20, 20)
        arr = np.zeros(shape, dtype=np.float32)
        arr[5:15, 5:15, 5:15] = 1.0
        img = itk.image_from_array(arr)
        img.SetSpacing([1.0, 1.0, 1.0])
        img.SetOrigin([0.0, 0.0, 0.0])
        img_path = paths.output / "activity.mhd"
        itk.imwrite(img, str(img_path))

        sim.world.size = [50 * gate.g4_units.cm] * 3
        sim.world.material = "G4_AIR"

        patient = sim.add_volume("Image", "patient")
        patient.image = str(img_path)
        patient.mother = "world"
        patient.material = "G4_WATER"
        patient.voxel_materials = [[0, 10, "G4_AIR"], [10, 10e6, "G4_WATER"]]

        src = sim.add_source("VoxelSource", "vox")
        src.attached_to = "patient"
        src.image = str(img_path)
        src.particle = "e-"
        src.energy.mono = 1 * MeV
        src.direction.type = "iso"
        src.number_of_primaries = 200

        # The trigger from the issue: a region user limit, implemented as a
        # Python G4VPhysicsConstructor which runs on every worker thread.
        sim.physics_manager.user_limits_particles = "electron"
        sim.physics_manager.set_min_ekine("patient", 10 * MeV)
        sim.physics_manager.set_production_cut("patient", "electron", 0.1 * mm)

        stats = sim.add_actor("SimulationStatisticsActor", "stats")

        sim.run()

        is_ok = stats.counts.events == 200
        utility.print_test(
            is_ok,
            f"Simulation generated {stats.counts.events} events (expected 200)",
        )

        # 1 master source + one source per worker thread
        expected_calls = 1 + number_of_threads
        is_ok = calls["count"] == expected_calls and is_ok
        utility.print_test(
            is_ok,
            f"CDF setter called {calls['count']} times "
            f"(expected {expected_calls}: once per thread-local source). "
            f"A larger count means worker threads re-apply the CDF.",
        )

        utility.test_ok(is_ok and cdf_ok)
    finally:
        g4.GateSPSVoxelsPosDistribution.SetCumulativeDistributionFunction = real_setter


if __name__ == "__main__":
    main()
