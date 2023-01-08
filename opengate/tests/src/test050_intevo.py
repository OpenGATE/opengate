#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec
import opengate.contrib.spect_siemens_intevo as gate_intevo

paths = gate.get_default_test_paths(__file__, "gate_test050_intevo")

# create the simulation
sim = gate.Simulation()

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
cm3 = gate.g4_units("cm3")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
BqmL = Bq / cm3
kBq = 1000 * Bq

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.number_of_threads = 1
ui.visu = True
# ui.random_seed = 321654987

# activity
activity = 1e3 * Bq / ui.number_of_threads

# world size
world = sim.world
world.size = [2.2 * m, 3.2 * m, 0.8 * m]
world.material = "G4_AIR"

# spect head
head = gate_intevo.add_intevo_spect_head(sim, "spect", collimator_type="LEHR")
# FIXME HE MELP LEHR no_collimator
# FIXME add the second head
# FIXME output digitizer -> to adapt to the source

# phantom IEC spheres
iec_phantom = gate_iec.add_phantom(sim)
iec_phantom.translation = [0 * cm, 3.5 * cm, 0 * cm]

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option3"
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 10 * mm
cuts.world.electron = 10 * mm
cuts.world.positron = 10 * mm
cuts.world.proton = 10 * mm
cuts.spect.gamma = 0.05 * mm
cuts.spect.electron = 0.01 * mm
cuts.spect.positron = 0.01 * mm

# sources IEC
# FIXME warning Ra224 to be changed in Tc99m ?
# FIXME maybe use voxelized CT and sources ?
ac = 2000 * BqmL
sources = gate_iec.add_spheres_sources(
    sim,
    "iec",
    "iec_source",
    [10, 13, 17, 22, 28, 37],
    [ac, ac, ac, ac, ac, ac],
    verbose=True,
)
for source in sources:
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "stats")
s.track_types_flag = True

# start simulation
output = sim.start()

# print results at the end
stat = output.get_actor("stats")
print(stat)

is_ok = True
gate.test_ok(is_ok)
