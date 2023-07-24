#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib

pathFile = pathlib.Path(__file__).parent.resolve()

# create the simulation
sim = gate.Simulation()
sim.add_material_database(pathFile / ".." / "data" / "GateMaterials.db")

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 1234567

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")
nm = gate.g4_units("nm")
mm = gate.g4_units("mm")

#  change world size
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# waterbox
waterbox = sim.create_and_add_volume("Box", "waterbox")
waterbox.size = [10 * cm, 10 * cm, 10 * cm]
waterbox.material = "Water"
waterbox.color = [0, 0, 1, 1]

# default source for tests
source = sim.add_source("GenericSource", "mysource")
source.energy.mono = 50 * MeV
source.particle = "proton"
source.position.type = "sphere"
source.position.radius = 1 * cm
source.direction.type = "iso"
source.activity = 10000 * Bq

# filter : keep gamma
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
fp = sim.add_filter("ParticleFilter", "fp")
fp.particle = "e-"

# add dose actor
dose = sim.add_actor("DoseActor", "dose")
dose.output = pathFile / ".." / "output" / "test023-edep.mhd"
# dose.output = 'output_ref/test023-edep.mhd'
dose.mother = "waterbox"
dose.size = [100, 100, 100]
dose.spacing = [2 * mm, 2 * mm, 2 * mm]
dose.filters.append(fp)

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True
s.filters.append(f)

print(s)
print(dose)
print("Filters: ", sim.filter_manager)
print(sim.filter_manager.dump())

# change physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMZ"
sim.physics_manager.global_production_cuts.all = 0.1 * mm

# start simulation
sim.run(start_new_process=True)

# print results at the end
stat = sim.output.get_actor("Stats")
print(stat)
# stat.write('output_ref/test023_stats.txt')

# tests
stats_ref = gate.read_stat_file(
    pathFile / ".." / "data" / "output_ref" / "test023_stats.txt"
)
is_ok = gate.assert_stats(stat, stats_ref, 0.8)
is_ok = is_ok and gate.assert_images(
    pathFile / ".." / "data" / "output_ref" / "test023-edep.mhd",
    pathFile / ".." / "output" / "test023-edep.mhd",
    stat,
    sum_tolerance=6,
    tolerance=50,
)

gate.test_ok(is_ok)
