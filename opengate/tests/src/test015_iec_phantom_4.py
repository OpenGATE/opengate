#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
from scipy.spatial.transform import Rotation
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()

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
mm = gate.g4_units("mm")
MeV = gate.g4_units("MeV")
KeV = gate.g4_units("keV")
Bq = gate.g4_units("Bq")
kBq = Bq * 1000
cm3 = gate.g4_units("cm3")
BqmL = Bq / cm3

#  change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# add a iec phantom
iec_phantom = gate_iec.add_phantom(sim)
iec_phantom.translation = [-5 * cm, -1 * cm, 2 * cm]
iec_phantom.rotation = Rotation.from_euler("z", 33, degrees=True).as_matrix()

# simple source
ac = 1000 * BqmL
sources = gate_iec.add_spheres_sources(
    sim, "iec", "iec_source", [10, 13, 17, 22, 28, 37], [ac, ac, ac, ac, ac, ac]
)
for s in sources:
    s.particle = "e-"
    s.energy.type = "mono"
    s.energy.mono = 1 * MeV

# Central source in "lung" compartment
name = iec_phantom.name
bg1 = sim.add_source("Generic", "bg1")
bg1.mother = f"{name}_center_cylinder_hole"
v = sim.get_volume_user_info(bg1.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f"Volume of {bg1.mother} {bg_volume} cm3")
bg1.position.type = "box"
bg1.position.size = gate.get_volume_bounding_box_size(sim, bg1.mother)
bg1.position.confine = bg1.mother
bg1.particle = "e-"
bg1.energy.type = "mono"
bg1.energy.mono = 1 * MeV
bg1.activity = ac * s.cubic_volume / 3  # ratio with spheres

# background source
# (I checked that source if confine only on mother, not including daughter volumes)
bg2 = sim.add_source("Generic", "bg2")
bg2.mother = f"{name}_interior"
v = sim.get_volume_user_info(bg2.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f"Volume of {bg2.mother} {bg_volume} cm3")
bg2.position.type = "box"
bg2.position.size = gate.get_volume_bounding_box_size(sim, bg2.mother)
bg2.position.confine = bg2.mother
bg2.particle = "e-"
bg2.energy.type = "mono"
bg2.energy.mono = 1 * MeV
bg2.activity = ac * s.cubic_volume / 10  # ratio with spheres

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "stats")
stats.track_types_flag = True

# add dose actor
dose = sim.add_actor("DoseActor", "dose")
dose.output = pathFile / ".." / "output" / "test015_confine.mhd"
# dose.output = 'output_ref/test015_confine.mhd'
dose.mother = "iec"
dose.size = [200, 200, 200]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]

# initialize & start
output = sim.start()

# Only for reference stats:
stats = output.get_actor("stats")
stats.write(pathFile / ".." / "output" / "test015_confine_stats.txt")
# stats.write('output_ref/test015_confine_stats.txt')

# check
stats_ref = gate.read_stat_file(
    pathFile / ".." / "data" / "output_ref" / "test015_confine_stats.txt"
)
is_ok = gate.assert_stats(stats, stats_ref, 0.03)
is_ok = is_ok and gate.assert_images(
    pathFile / ".." / "data" / "output_ref" / "test015_confine.mhd",
    pathFile / ".." / "output" / "test015_confine.mhd",
    stats,
    tolerance=78,
)

gate.test_ok(is_ok)
