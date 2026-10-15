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
"""

import numpy as np
import itk

import opengate as gate
from opengate.tests import utility
import opengate_core as g4


def main():
    paths = utility.get_default_test_paths(__file__, output_folder="test115_mt")

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

        utility.test_ok(is_ok)
    finally:
        g4.GateSPSVoxelsPosDistribution.SetCumulativeDistributionFunction = real_setter


if __name__ == "__main__":
    main()
