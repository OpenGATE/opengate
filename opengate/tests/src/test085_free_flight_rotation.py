#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.logger
import opengate.contrib.spect.ge_discovery_nm670 as nm670
from opengate import g4_units
from opengate.tests import utility
from test085_free_flight_helpers import create_simulation_test085


if __name__ == "__main__":

    paths = utility.get_default_test_paths(__file__, None, output_folder="test085")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 1
    create_simulation_test085(sim, paths, ac=1e6)
    sim.running_verbose_level = opengate.logger.RUN

    arf1 = sim.get_actor("detector_arf_1")
    arf2 = sim.get_actor("detector_arf_2")
    arf1.output_filename = "projection_ff_1.mhd"
    arf2.output_filename = "projection_ff_2.mhd"

    stats = sim.get_actor("stats")
    stats.output_filename = "stats_ff.txt"
    sim.json_archive_filename = "simu_ff.json"

    # free flight actor
    ff = sim.add_actor("FreeFlightActor", "ff")
    ff.attached_to = "phantom"
    ff.particles = "gamma"

    # compute the gantry rotations
    det_plane1 = sim.volume_manager.get_volume("detector_1")
    det_plane2 = sim.volume_manager.get_volume("detector_2")
    n = 60
    total_time = 1 * g4_units.s
    step_time = total_time / n
    sim.run_timing_intervals = [[i * step_time, (i + 1) * step_time] for i in range(n)]
    radius = 20 * g4_units.cm
    step_angle = 180 / n
    nm670.rotate_gantry(det_plane1, radius, 0, step_angle, n)
    nm670.rotate_gantry(det_plane2, radius, 180, step_angle, n)

    # sim.dyn_geom_open_close = False
    # sim.dyn_geom_optimise = False

    # go
    sim.run()
    stats = sim.get_actor("stats")
    print(stats)
