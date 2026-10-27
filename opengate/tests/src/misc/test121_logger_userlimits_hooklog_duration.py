#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Small API fixes:
- #1096: opengate keeps the loguru handlers added by the user.
- #356: the user limit setters accept a 'particles' keyword.
- #448: user_hook_log is a dictionary (append() still works, deprecated).
- #1086: the duration in the statistics only counts the event loop.
"""

from loguru import logger

import opengate as gate
from opengate.tests import utility

mm = gate.g4_units.mm
cm = gate.g4_units.cm
MeV = gate.g4_units.MeV
sec = gate.g4_units.s


def hook_after_run(simulation_engine):
    # named entry
    simulation_engine.user_hook_log["my_entry"] = {"value": 42}
    # deprecated list-like interface, still accepted
    simulation_engine.user_hook_log.append("legacy")


def create_simulation(paths, n):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.world.size = [1 * gate.g4_units.m] * 3
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [30 * cm] * 3
    waterbox.material = "G4_WATER"
    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.direction.type = "iso"
    source.number_of_primaries = n
    # a large dose image: allocating and writing it takes time at the beginning
    # and end of the run, which must not be counted in the duration
    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = "waterbox"
    dose.size = [100, 100, 100]
    dose.spacing = [3 * mm] * 3
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    return sim, stats


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test121")
    is_ok = True

    # --- #1096: a user's loguru handler is kept by opengate
    messages = []
    user_handler = logger.add(messages.append, level="INFO")
    sim, stats = create_simulation(paths, 1)
    sim.verbose_level = gate.logger.INFO
    logger.info("message from the user")
    b = any("message from the user" in str(m) for m in messages)
    utility.print_test(b, "A user loguru handler is kept after creating a Simulation")
    is_ok = is_ok and b

    # --- #356: particles keyword of the user limit setters
    sim.physics_manager.set_max_step_size("waterbox", 1 * mm, particles="proton")
    sim.volume_manager.volumes["waterbox"].set_min_ekine(1 * MeV, particles=["e-"])
    pl = list(sim.physics_manager.user_limits_particles)
    b = pl == ["all_charged", "proton", "e-"]
    utility.print_test(b, f"user_limits_particles extended by the setters: {pl}")
    is_ok = is_ok and b
    region = sim.physics_manager.find_or_create_region("waterbox")
    b = region.user_limits["max_step_size"] == 1 * mm
    b = b and region.user_limits["min_ekine"] == 1 * MeV
    utility.print_test(b, "user limits set in the region of the volume")
    is_ok = is_ok and b

    # --- #448: user_hook_log is a dictionary
    sim.user_hook_after_run = hook_after_run
    sim.run(start_new_process=True)
    log = sim.user_hook_log
    b = log["my_entry"]["value"] == 42 and log.my_entry.value == 42
    b = b and log["entry_1"] == "legacy"
    utility.print_test(b, f"user_hook_log is a dictionary: {dict(log)}")
    is_ok = is_ok and b

    # --- #1086: with a single event, the duration is (almost) zero although the
    # large dose image takes time to set up and write
    duration = stats.counts.duration / sec
    init = stats.counts.init / sec
    b = stats.counts.events == 1 and duration < 0.1
    utility.print_test(
        b, f"Duration of 1 event: {duration:.4f} s (init {init:.2f} s) < 0.1 s"
    )
    is_ok = is_ok and b

    logger.remove(user_handler)
    utility.test_ok(is_ok)
