#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression test for the user-limit physics constructor in multi-threaded runs
(see #1163).

The user-limit processes are added by a C++ Geant4 physics constructor
(GateUserLimitsPhysics). Geant4 calls its ConstructProcess() on every worker
thread while G4MTRunManager::Initialize() runs. When the constructor was
implemented in Python, each worker had to re-enter the interpreter and take
the GIL while the master thread could hold the MT barrier, which deadlocked
the initialisation of runs with region user limits and several workers.

This test runs a small simulation with 8 workers and a region user limit, and
checks that the run completes and that the expected processes are attached to
the selected particle.
"""

import opengate as gate
import opengate_core as g4
from opengate.tests import utility


def check_processes(simulation_engine):
    pm = g4.G4ParticleTable.GetParticleTable().FindParticle("e-").GetProcessManager()
    simulation_engine.user_hook_log["has_step_limiter"] = (
        pm.GetProcess("StepLimiter") is not None
    )
    simulation_engine.user_hook_log["has_user_special_cut"] = (
        pm.GetProcess("UserSpecialCut") is not None
    )


def main():
    paths = utility.get_default_test_paths(__file__, output_folder="test133_mt")

    sim = gate.Simulation()
    sim.number_of_threads = 8
    sim.random_seed = 123456
    sim.output_dir = paths.output

    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    sim.world.size = [50 * gate.g4_units.cm] * 3
    sim.world.material = "G4_AIR"

    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [10 * gate.g4_units.cm] * 3
    waterbox.material = "G4_WATER"

    sim.physics_manager.user_limits_particles = "electron"
    sim.physics_manager.set_min_ekine(waterbox.name, 10 * MeV)
    sim.physics_manager.set_max_step_size(waterbox.name, 1 * mm)

    source = sim.add_source("GenericSource", "e-")
    source.particle = "e-"
    source.energy.mono = 20 * MeV
    source.position.radius = 1 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 20

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.user_hook_after_init = check_processes
    sim.run()

    is_ok = stats.counts.events == 20
    utility.print_test(
        is_ok, f"Simulation generated {stats.counts.events} events (expected 20)"
    )

    b = sim.user_hook_log["has_step_limiter"] is True
    utility.print_test(b, "electron has the StepLimiter process")
    is_ok = is_ok and b

    b = sim.user_hook_log["has_user_special_cut"] is True
    utility.print_test(b, "electron has the UserSpecialCut process")
    is_ok = is_ok and b

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
