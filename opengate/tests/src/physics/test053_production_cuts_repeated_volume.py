#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Issue #1275: a region (production cuts, user limits, EM switches) set on a
volume repeated with RepeatParametrisedVolume made the simulation crash
(segmentation fault) at the first step in that volume. Geant4 does not support
a region that starts at a parameterised volume: the region of the mother takes
it over, and the volume gets no material-cuts couple.

Such a region now stops the simulation at the configuration with a message
that says to set it on the mother volume. A region on the mother volume
works, and applies to the repeated volumes.
"""

import opengate as gate
from opengate.tests import utility
from opengate.geometry.volumes import RepeatParametrisedVolume

mm = gate.g4_units.mm
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq


def create_simulation():
    sim = gate.Simulation()
    sim.random_seed = 1234
    sim.world.size = [500 * mm] * 3
    sim.world.material = "G4_AIR"

    detector = sim.add_volume("Box", "detector")
    detector.size = [24.6 * mm, 24.6 * mm, 6 * mm]
    detector.material = "G4_AIR"

    pixel = sim.add_volume("Box", "pixel")
    pixel.mother = detector
    pixel.size = [2.46 * mm, 2.46 * mm, 6 * mm]
    pixel.material = "G4_CADMIUM_TELLURIDE"

    param = RepeatParametrisedVolume(repeated_volume=pixel)
    param.linear_repeat = [10, 10, 1]
    param.translation = [2.46 * mm, 2.46 * mm, 0]
    param.start = "auto"
    sim.volume_manager.add_volume(param)

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "box"
    source.position.size = [10 * mm, 10 * mm, 0]
    source.position.translation = [0, 0, 100 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.activity = 1000 * Bq

    sim.add_actor("SimulationStatisticsActor", "stats")
    return sim


def expect_error(label, set_region):
    sim = create_simulation()
    set_region(sim)
    try:
        sim.run(start_new_process=False)
    except Exception as e:
        msg = str(e).strip().splitlines()[-1]
        print(f"Expected error: {msg}")
        b = "mother volume 'detector'" in msg
        utility.print_test(b, f"{label}: stopped with a message")
        return b
    utility.print_test(False, f"{label}: no error")
    return False


def hook_after_run(se):
    # the region of the mother applies to the repeated volume, which has a
    # material-cuts couple (no couple: crash at the first step in the volume)
    lv = se.simulation.volume_manager.get_volume("pixel").g4_logical_volume
    region = lv.GetRegion()
    se.user_hook_log.pixel_region = region.GetName() if region else None
    se.user_hook_log.pixel_has_couple = lv.GetMaterialCutsCouple() is not None


if __name__ == "__main__":
    is_ok = True

    # production cut on the repeated volume
    is_ok = (
        expect_error(
            "production cut on 'pixel'",
            lambda s: s.physics_manager.set_production_cut("pixel", "gamma", 0.01 * mm),
        )
        and is_ok
    )

    # user limit on the repeated volume (same crash before the fix)
    def max_step(s):
        s.physics_manager.set_max_step_size("pixel", 0.1 * mm)
        s.physics_manager.user_limits_particles = ["gamma"]

    is_ok = expect_error("max step size on 'pixel'", max_step) and is_ok

    # production cut on the RepeatParametrisedVolume itself
    is_ok = (
        expect_error(
            "production cut on 'pixel_param'",
            lambda s: s.physics_manager.set_production_cut(
                "pixel_param", "gamma", 0.01 * mm
            ),
        )
        and is_ok
    )

    # production cut on the mother volume: runs
    sim = create_simulation()
    sim.physics_manager.set_production_cut("detector", "gamma", 0.01 * mm)
    sim.user_hook_after_run = hook_after_run
    sim.run(start_new_process=False)
    stats = sim.get_actor("stats")
    print(stats)
    region_name = sim.user_hook_log.pixel_region
    has_couple = sim.user_hook_log.pixel_has_couple
    b = stats.counts.events > 0 and region_name == "detector_region" and has_couple
    utility.print_test(
        b,
        f"production cut on 'detector': {stats.counts.events} events, "
        f"region of 'pixel' = {region_name}, couple = {has_couple}",
    )
    is_ok = b and is_ok

    utility.test_ok(is_ok)
