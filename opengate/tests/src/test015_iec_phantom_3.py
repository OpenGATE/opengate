#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
from scipy.spatial.transform import Rotation
import pathlib
import os

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

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
cm3 = gate.g4_units("cm3")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3
print("Unit Bq", Bq)
print("Unit mL (cm3)", cm3)
print("Unit BqmL", BqmL)

# change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a iec phantom
iec_phantom = gate_iec.add_phantom(sim)
iec_phantom.translation = [3 * cm, 1 * cm, 0 * cm]
iec_phantom.rotation = Rotation.from_euler("y", 33, degrees=True).as_matrix()

# simple source
# gate_iec.add_sources(sim, 'iec', 'all')
ac = 2000 * BqmL
gate_iec.add_spheres_sources(
    sim,
    "iec",
    "iec_source",
    [10, 13, 17, 22, 28, 37],
    # [ac, 0, 0, 0, 0, 0])
    [ac, ac, ac, ac, ac, ac],
    verbose=True,
)

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "stats")
stats.track_types_flag = True

# add dose actor
dose = sim.add_actor("DoseActor", "dose")
dose.output = pathFile / ".." / "output" / "test015.mhd"
# dose.output = 'output_ref/test015_ref.mhd'
dose.mother = "iec"
dose.size = [100, 100, 100]
mm = gate.g4_units("mm")
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.translation = [0 * mm, 0 * mm, 0 * mm]

# run timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 1 * sec]]

print(sim.volume_manager.dump_tree_of_volumes())
print(sim.source_manager.dump())

# initialize & start
output = sim.start()

# Only for reference stats:
stats = output.get_actor("stats")
# stats.write('output_ref/test015_stats.txt')

# check
stats_ref = gate.read_stat_file(
    pathFile / ".." / "data" / "output_ref" / "test015_stats.txt"
)
is_ok = gate.assert_stats(stats, stats_ref, 0.07)
is_ok = is_ok and gate.assert_images(
    pathFile / ".." / "data" / "output_ref" / "test015_ref.mhd",
    pathFile / ".." / "output" / "test015.mhd",
    stats,
    tolerance=65,
)

gate.test_ok(is_ok)
