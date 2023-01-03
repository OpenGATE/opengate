#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()


# global log level
# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 123654987

#  change world size
m = gate.g4_units("m")
cm = gate.g4_units("cm")
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]

# add a iec phantom
iec_phantom = gate_iec.add_phantom_old(sim)
iec_phantom.translation = [0 * cm, 3.5 * cm, 0 * cm]

# simple source
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
source = sim.add_source("Generic", "g")
source.particle = "gamma"
source.energy.mono = 0.1 * MeV
source.direction.type = "iso"
source.activity = 50000 * Bq

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "stats")
stats.track_types_flag = True

# run timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 1 * sec]]

# initialize & start
output = sim.start()

# print results at the end
stats = output.get_actor("stats")
print(stats)
stats.write(pathFile / ".." / "output" / "stats_test015_iec_phantom_1.txt")

# check
stats_ref = gate.SimulationStatisticsActor()
c = stats_ref.counts
c.run_count = 1
c.event_count = 49997
c.track_count = 53027
c.step_count = 468582
# stats_ref.pps = 2150
sec = gate.g4_units("second")
c.duration = c.event_count / 19441.5 * sec
print("-" * 80)
is_ok = gate.assert_stats(stats, stats_ref, 0.06)

gate.test_ok(is_ok)
