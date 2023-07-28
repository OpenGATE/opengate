#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec

paths = gate.get_default_test_paths(__file__, "")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
# ui.visu = True
ui.visu_type = "vrml"
ui.check_volumes_overlap = True

# world size
m = gate.g4_units("m")
cm = gate.g4_units("cm")
world = sim.world
world.size = [0.5 * m, 0.5 * m, 0.5 * m]

# add a iec phantom
iec_phantom = gate_iec.add_iec_phantom(sim)
iec_phantom.translation = [0 * cm, 0 * cm, 0 * cm]

# simple fake source
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
source = sim.add_source("GenericSource", "g")
source.particle = "gamma"
source.energy.mono = 0.1 * MeV
source.direction.type = "iso"
source.activity = 50 * Bq

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "stats")
stats.track_types_flag = True

# run timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 1 * sec]]

# initialize & start
sim.run()

# print results at the end
stats = sim.output.get_actor("stats")
print(stats)

# Look at the spheres positions ?
spheres_diam = [10, 13, 17, 22, 28, 37]
for diam in spheres_diam:
    mm = gate.g4_units("mm")
    cm = gate.g4_units("cm")
    d = f"{(diam / mm):.0f}mm"
    name = f"iec_sphere_{d}"
    s = sim.get_volume_user_info(name)
    print(name, s.translation)

is_ok = False
gate.test_ok(is_ok)
