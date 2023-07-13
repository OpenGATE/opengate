#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from helpers import *

# create the simulation
sim = gate.Simulation()
simu_name = "main0_orientation"

# options
ui = sim.user_info
ui.number_of_threads = 1
ui.visu = False
ui.visu_type = "vrml"
ui.check_volumes_overlap = True
mm = gate.g4_units("mm")
m = gate.g4_units("m")
keV = gate.g4_units("keV")
cm3 = gate.g4_units("cm3")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3

sim.world.size = [1 * m, 1 * m, 1 * m]

# main elements : spect + phantom
# head, digit = create_simu_with_intevo(sim, debug=ui.visu)

# add IEC phantom
iec1 = gate_iec.add_phantom(sim, name="iec")
# iec1.translation = [0, 0, 500*mm]

# iec2 = gate_iec.add_phantom_old(sim, name='iec_old')
# iec2.translation = [0, 0, 500*mm]

# add table
# sim.add_parallel_world("world2")
# bed = gate_intevo.add_fake_table(sim)
# bed.mother = "world2"

# rotation by default
# head.translation = [450 * mm, 0, 0]
# head.rotation = Rotation.identity().as_matrix()

# stats
sim.add_actor("SimulationStatisticsActor", "stats")

# fake source
source = sim.add_source("GenericSource", "Default")
source.particle = "gamma"
source.energy.mono = 80 * keV
source.direction.type = "iso"
source.n = 1e1

s = gate_iec.add_background_source(sim, "iec", "bg", 1 * BqmL, True)
s.particle = "gamma"
s.energy.type = "mono"
s.energy.mono = 10 * keV

sim.set_production_cut("world", "all", 100 * m)

# phsp
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.attributes = [
    "KineticEnergy",
    "EventPosition",
]
phsp.output = "iec.root"

# run (no source, only for visualisation)
# sim.run()
se = gate.SimulationEngine(sim, start_new_process=False)
print(se)
output = se.start()
se.check_volumes_overlap(True)

stats = output.get_actor("stats")
print(stats)
