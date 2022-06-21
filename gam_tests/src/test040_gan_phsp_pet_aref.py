#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.phantom_nema_iec_body as gam_iec

paths = gam.get_default_test_paths(__file__, '')
paths.output_ref = paths.output_ref / 'test040_ref'

# create the simulation
sim = gam.Simulation()

# units
m = gam.g4_units('m')
cm = gam.g4_units('cm')
cm3 = gam.g4_units('cm3')
keV = gam.g4_units('keV')
mm = gam.g4_units('mm')
Bq = gam.g4_units('Bq')
BqmL = Bq / cm3
sec = gam.g4_units('second')
deg = gam.g4_units('deg')
kBq = 1000 * Bq
MBq = 1000 * kBq

# main parameters
ui = sim.user_info
ui.check_volumes_overlap = True
ui.number_of_threads = 1
ac = 5e3 * BqmL / ui.number_of_threads
ui.visu = False
colli_flag = not ui.visu
if ui.visu:
    ac = 1 * BqmL  # per mL
    ui.number_of_threads = 1

# world size
world = sim.world
world.size = [1.5 * m, 1.5 * m, 1.5 * m]
world.material = 'G4_AIR'

# iec phantom
iec_phantom = gam_iec.add_phantom(sim)

# test phase space
phsp_sphere_surface = sim.add_volume('Sphere', 'phase_space_sphere')
phsp_sphere_surface.rmin = 215 * mm
phsp_sphere_surface.rmax = 216 * mm
phsp_sphere_surface.color = [1, 1, 1, 1]
phsp_sphere_surface.material = 'G4_AIR'

# physic list
sim.set_cut('world', 'all', 1 * mm)

# source sphere
gam_iec.add_spheres_sources(sim, 'iec', 'source1',
                            [10, 13, 17, 22, 28, 37],
                            [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac],
                            verbose=True)

# with acceptance angle (?) # FIXME
sources = sim.source_manager.user_info_sources
for source in sources.values():
    source.particle = 'e+'
    source.energy.type = 'Ga68'
    source.direction.type = 'iso'

# background source 1:10 ratio with sphere
# bg = gam_iec.add_background_source(sim, 'iec', 'source_bg', ac / 10, verbose=True)

# add stat actor
stat = sim.add_actor('SimulationStatisticsActor', 'Stats')
stat.output = paths.output / 'test040_ref_stats.txt'

# store phsp of exiting particles (gamma only)
phsp = sim.add_actor('PhaseSpaceActor', 'phsp')
phsp.mother = phsp_sphere_surface.name
phsp.attributes = ['KineticEnergy', 'PrePosition', 'PreDirection',
                   'GlobalTime', 'TimeFromBeginOfEvent',
                   'EventPosition', 'EventDirection',
                   'EventKineticEnergy']
phsp.output = paths.output / 'test040_ref_phsp.root'
f = sim.add_filter('ParticleFilter', 'f')
f.particle = 'gamma'
phsp.filters.append(f)
f = sim.add_filter('KineticEnergyFilter', 'f')
f.energy_min = 100 * keV
phsp.filters.append(f)

# go
sim.initialize()
sim.start()

# ----------------------------------------------------------------------------------------------------------

# check stats
print()
gam.warning(f'Check stats')
stats = sim.get_actor('Stats')
print(stats)
stats_ref = gam.read_stat_file(paths.output_ref / 'test040_ref_stats.txt')
is_ok = gam.assert_stats(stats, stats_ref, 0.01)

# No other tests here for the moment, will be used by test040_gan
gam.test_ok(is_ok)
