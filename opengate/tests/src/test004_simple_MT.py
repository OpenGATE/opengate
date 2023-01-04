#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "gate_test004_simulation_stats_actor")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.running_verbose_level = 0
ui.visu = False
ui.number_of_threads = 5
# special debug mode : force MT even with one single thread
ui.force_multithread_mode = True
ui.random_engine = "MixMaxRng"
ui.random_seed = "auto"

"""
    Warning: we can only see the speed up of the MT mode for large nb of particles (>2e6)
"""

# set the world size like in the Gate macro
m = gate.g4_units("m")
world = sim.world
world.size = [3 * m, 3 * m, 3 * m]
world.material = "G4_AIR"

# add a simple waterbox volume
waterbox = sim.add_volume("Box", "Waterbox")
cm = gate.g4_units("cm")
waterbox.size = [40 * cm, 40 * cm, 40 * cm]
waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
waterbox.material = "G4_WATER"

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMV"
cuts = p.production_cuts
um = gate.g4_units("um")
cuts.world.gamma = 700 * um
cuts.world.electron = 700 * um
cuts.world.positron = 700 * um
cuts.world.proton = 700 * um

# default source for tests
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
source = sim.add_source("Generic", "Default")
source.particle = "gamma"
source.energy.mono = 80 * keV
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.n = 200000 / ui.number_of_threads

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# start simulation
# sim.apply_g4_command("/run/verbose 0")
# sim.apply_g4_command("/run/eventModulo 5000 1")
output = sim.start()

# get results
stats = output.get_actor("Stats")
print(stats)
print("track type", stats.counts.track_types)

# gate_test4_simulation_stats_actor
# Gate mac/main.mac
stats_ref = gate.read_stat_file(paths.gate_output / "stat.txt")
stats_ref.counts.run_count = sim.user_info.number_of_threads
is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.01)

gate.test_ok(is_ok)
