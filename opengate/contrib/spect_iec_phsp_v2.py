#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec

# global log level

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_engine = "MersenneTwister"
ui.random_seed = "auto"
ui.number_of_threads = 6

# change world size
m = gate.g4_units("m")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
world = sim.world
world.size = [1 * m, 1 * m, 1 * m]

# phase-space surface
phsp = sim.add_volume("Sphere", "phsp")
phsp.material = world.material
phsp.rmax = 30 * cm
phsp.rmin = phsp.rmax - 1 * nm
phsp.color = [1, 1, 0, 1]

# add a iec phantom
iec_phantom = gate_iec.add_phantom(sim)

# add all sphere sources
Bq = gate.g4_units("Bq")
kBq = gate.g4_units("Bq") * 1000
gamma_yield = 0.986  # if gamma, consider yield 98.6%
ac = 50 * kBq * gamma_yield
ac = 1e2 * Bq

# source1
gate_iec.add_spheres_sources(
    sim,
    "iec",
    "source1",  # [28], [ac])
    [10, 13, 17, 22, 28, 37],
    [ac, ac, ac, ac, ac * 2, ac],
)

# source2
gate_iec.add_spheres_sources(
    sim,
    "iec",
    "source2",  # [28], [ac])
    [10, 13, 17, 22, 28, 37],
    [ac, ac, ac, ac, ac, ac / 2],
)

# Background source
"""bg1 = sim.add_source('Generic', 'bg1')
bg1.mother = f'{name}_center_cylinder_hole'
v = sim.get_volume_user_info(bg1.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f'Volume of {bg1.mother} {bg_volume} cm3')
bg1.position.type = 'box'
bg1.position.size = gate.get_max_size_from_volume(sim, bg1.mother)
bg1.position.confine = bg1.mother
bg1.particle = p
bg1.energy.type = 'F18'
w = 1
bg1.activity = ac * bg_volume / 3 / w  # ratio with spheres
bg1.weight = w

# background source
# (I checked that source if confine only on mother, not including daughter volumes)
bg2 = sim.add_source('Generic', 'bg2')
bg2.mother = f'{name}_interior'
v = sim.get_volume_user_info(bg2.mother)
s = sim.get_solid_info(v)
bg_volume = s.cubic_volume / cm3
print(f'Volume of {bg2.mother} {bg_volume} cm3')
bg2.position.type = 'box'
bg2.position.size = gate.get_max_size_from_volume(sim, bg2.mother)
bg2.position.confine = bg2.mother
bg2.particle = p
bg2.energy.type = 'F18'
w = 20
bg2.activity = ac * bg_volume / 10 / w  # ratio with spheres
bg2.weight = w"""

# modify the source type, set to Tc99m
sources = sim.source_manager.user_info_sources
MeV = gate.g4_units("MeV")
for source in sources.values():
    source.energy.type = "mono"
    # source.particle = 'ion 43 99 143'  # Tc99m metastable: E = 143
    # source.energy.mono = 0
    source.particle = "gamma"
    source.energy.type = "gauss"  # or 'mono'
    if "source1" in source.name:
        source.energy.mono = 0.1 * MeV
    if "source2" in source.name:
        source.energy.mono = 0.5 * MeV
    source.energy.sigma_gauss = 0.05 * MeV

# add stat actor
stats = sim.add_actor("SimulationStatisticsActor", "stats")
stats.track_types_flag = True

# with PhaseSpaceActor
ta = sim.add_actor("PhaseSpaceActor", "phase_space")
ta.mother = "phsp"
ta.attributes = [
    "KineticEnergy",
    "PostPosition",
    "PostDirection",
    "TimeFromBeginOfEvent",  # 'TrackEnergy',
    "EventID",
    "EventPosition",
    "TrackVertexMomentumDirection",
    "TrackVertexKineticEnergy",
]
ta.output = "./output/spect_iec.root"

# FIXME
# f = sim.add_filter('particle')
# f.actor = 'phsp'
# f.particle = 'gamma'

# phys
mm = gate.g4_units("mm")
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = False  # not needed if gamma, needed if ion
cuts = p.production_cuts
cuts.world.gamma = 1 * mm
cuts.world.electron = 1 * mm
cuts.world.positron = 1 * mm

# run timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 1 * sec]]

# initialize & start
sim.initialize()
for source in sources.values():
    print(source)

# sim.apply_g4_command("/tracking/verbose 1")

sim.start()

# print results at the end
stats = sim.get_actor("stats")
print(stats)
stats.write("output/stats.txt")

# compare ?
import gatetools.phsp as phsp

# phsp.
