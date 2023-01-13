#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantom_nema_iec_body as gate_iec

paths = gate.get_default_test_paths(__file__, "")
paths.output_ref = paths.output_ref / "test040_ref"

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
sec = gate.g4_units("second")
deg = gate.g4_units("deg")
kBq = 1000 * Bq
MBq = 1000 * kBq

# main parameters
ui = sim.user_info
ui.check_volumes_overlap = True
ui.number_of_threads = 1
ui.random_seed = 123456
ac = 5e3 * BqmL / ui.number_of_threads
ui.visu = False
colli_flag = not ui.visu
if ui.visu:
    ac = 1 * BqmL  # per mL
    ui.number_of_threads = 1

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = "G4_AIR"

# iec phantom
iec_phantom = gate_iec.add_phantom(sim)

# add an artificial tungsten bar
vint = sim.get_volume_user_info("iec_interior")
print(vint)
t = sim.add_volume("Box", "tung")
t.mother = vint.name
t.size = [3 * cm, 8 * cm, 10 * cm]
t.translation = [-9 * cm, 5 * cm, 5 * cm]
t.material = "G4_CADMIUM_TUNGSTATE"
t.color = [0, 0, 1, 1]

# test phase space
phsp_sphere_surface = sim.add_volume("Sphere", "phase_space_sphere")
phsp_sphere_surface.rmin = 215 * mm
phsp_sphere_surface.rmax = 216 * mm
phsp_sphere_surface.color = [1, 1, 1, 1]
phsp_sphere_surface.material = "G4_AIR"

# physic list
sim.set_cut("world", "all", 1 * mm)

# source sphere
gate_iec.add_spheres_sources(
    sim,
    "iec",
    "source1",
    [10, 13, 17, 22, 28, 37],
    [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac],
    verbose=True,
)

# with acceptance angle (?) # FIXME
sources = sim.source_manager.user_info_sources
for source in sources.values():
    source.particle = "e+"
    source.energy.type = "Ga68"
    source.direction.type = "iso"

# background source 1:10 ratio with sphere
# bg = gate_iec.add_background_source(sim, 'iec', 'source_bg', ac / 10, verbose=True)

# add stat actor
stat = sim.add_actor("SimulationStatisticsActor", "Stats")
stat.output = paths.output / "test040_ref_stats.txt"

# store phsp of exiting particles (gamma only)
phsp = sim.add_actor("PhaseSpaceActor", "phsp")
phsp.mother = phsp_sphere_surface.name
phsp.attributes = [
    "KineticEnergy",
    "PrePosition",
    "PreDirection",
    "GlobalTime",
    "TimeFromBeginOfEvent",
    "EventID",
    "EventPosition",
    "EventDirection",
    "EventKineticEnergy",
]
phsp.output = paths.output / "test040_ref_phsp.root"
phsp.store_absorbed_event = True
f = sim.add_filter("ParticleFilter", "f")
f.particle = "gamma"
phsp.filters.append(f)
f = sim.add_filter("KineticEnergyFilter", "f")
f.energy_min = 100 * keV
phsp.filters.append(f)

# go
output = sim.start()

# ----------------------------------------------------------------------------------------------------------

# check stats
print()
gate.warning(f"Check stats")
stats = output.get_actor("Stats")
print(stats)
stats_ref = gate.read_stat_file(paths.output_ref / "test040_ref_stats.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.01)

# 426760*2*0.8883814158496728 = 758251.3

phsp = output.get_actor("phsp")
ref = 17299
ae = phsp.user_info.fNumberOfAbsorbedEvents
err = abs(ae - ref) / ref
tol = 0.02
is_ok = err < tol and is_ok
gate.print_test(is_ok, f"Number of absorbed events: {ae} vs {ref} = {err * 100:.2f}%")

# No other tests here for the moment, will be used by test040_gan
gate.test_ok(is_ok)
