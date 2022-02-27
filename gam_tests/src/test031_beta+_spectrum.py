#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import gam_gate as gam
import uproot

paths = gam.get_common_test_paths(__file__, '')

l = gam.all_beta_plus_radionuclides
# l = ['F18', 'Ga68', 'O15']
# l = ['F18']

# references (02/2022)
# http://www.lnhb.fr/nuclear-data/module-lara/
rad_yields = {'F18': 0.968600992766,
              'Ga68': 0.8883814158496728,
              'Zr89': 0.22799992881708,
              'Na22': 0.8972935562750121,
              'C11': 0.9974862363857401,
              'N13': 0.9981749688051,
              'O15': 0.9988401691350001,
              'Rb82': 0.95410853035736}

# Get one color for each rad
fig, ax1 = plt.subplots(1, 1, figsize=(20, 10))
cmap = plt.get_cmap('Dark2')
rad_color = {}
n = len(l)
i = 0
for rad in l:
    rad_color[rad] = cmap(i / n)
    i += 1

for rad in l:
    data = gam.read_beta_plus_spectra(rad)
    x = data[:, 0]  # energy E(keV)
    y = data[:, 1]  # proba  dNtot/dE b+
    # normalize taking into account the bins density
    dx = gam.compute_bins_density(x)
    s = (y * dx).sum()
    y = y / s
    ax1.plot(x, y, label=rad, color=rad_color[rad])

plt.xlabel('Energy KeV')
plt.ylabel('Probability')
ax1.legend()
plt.text(2200, 0.0023, "BetaShape")
plt.text(2200, 0.0020, "Mougeot, Phys Rev C 91, 055504 (2015)")
plt.text(2200, 0.0017, "http://www.lnhb.fr/nuclear-data/module-lara")

# units
cm = gam.g4_units('cm')
m = gam.g4_units('m')
Bq = gam.g4_units('Bq')

# simulation
sim = gam.Simulation()
sim.user_info.visu = False
sim.world.size = [1 * m, 1 * m, 1 * m]
sim.world.material = 'G4_Galactic'


def add_box(i):
    b = sim.add_volume('Box', f'b{i}')
    b.size = [1 * cm, 1 * cm, 1 * cm]
    b.translation = [2 * i * cm, 0 * cm, 0 * cm]
    b.material = 'G4_Galactic'


tol = 0.03


def add_source(rad):
    si = len(rads)
    add_box(si)
    source = sim.add_source('Generic', f'source_{rad}')
    source.mother = f'b{si}'
    source.particle = 'e+'
    source.energy.type = f'{rad}'
    source.position.type = 'point'
    source.direction.type = 'iso'
    # with real simulation, the activity should be weighted by the total yield
    total_yield = gam.get_rad_yield(rad)
    source.activity = activity  # * total_yield
    yi = rad_yields[rad]
    t = (total_yield - yi) / yi < tol
    gam.print_test(t, f'Rad {rad} total yield = {total_yield} vs {yi} (tol is {tol})')

    phsp = sim.add_actor('PhaseSpaceActor', f'phsp_{rad}')
    phsp.mother = f'b{si}'
    phsp.attributes = ['TrackVertexKineticEnergy']
    phsp.output = paths.output / f'test031_{rad}.root'
    f = sim.add_filter('ParticleFilter', 'f')
    f.particle = 'e+'
    phsp.filters.append(f)
    rads.append(rad)


rads = []
activity = 100000 * Bq
for r in l:
    add_source(r)

"""
add_source('F18_analytic')
rad_color['F18_analytic'] = rad_color['F18']
add_source('O15_analytic')
rad_color['O15_analytic'] = rad_color['O15']
add_source('C11_analytic')
rad_color['C11_analytic'] = rad_color['C11']
"""

s = sim.add_actor('SimulationStatisticsActor', 'stats')
s.track_types_flag = True

sim.initialize()
sim.start()

# print results
stats = sim.get_actor('stats')
print(stats)

# plot
for i in range(len(rads)):
    rad = rads[i]
    output = paths.output / f'test031_{rad}.root'
    data = uproot.open(output)[f'phsp_{rad}']
    data = data.arrays(library="numpy")['TrackVertexKineticEnergy'] * 1000  # MeV to KeV
    ax1.hist(data, bins=200, density=True, histtype='stepfilled', alpha=0.5,
             label=f'{rads[i]}', color=rad_color[rad])

f = paths.output / 'test031.png'
ax1.legend(loc='upper center')
plt.savefig(f)
print(f'Figure save in {f}')

# compute diff
# ax2 = ax1.twinx()
is_ok = True
tol = 4
for rad in rads:
    # input
    output = paths.output_ref / f'test031_{rad}.root'
    data_ref = uproot.open(output)[f'phsp_{rad}']
    data_ref = data_ref.arrays(library="numpy")['TrackVertexKineticEnergy'] * 1000  # MeV to KeV
    hist_ref, bins_ref = np.histogram(data_ref, range=(data_ref.min(), data_ref.max()),
                                      bins=100, density=False)
    """ax2.hist(data_ref, bins=100, density=False,
             range=(data_ref.min(), data_ref.max()), histtype='stepfilled',
             alpha=0.5, label=f'{rads[i]}', color='r')"""
    # output
    output = paths.output / f'test031_{rad}.root'
    data = uproot.open(output)[f'phsp_{rad}']
    data = data.arrays(library="numpy")['TrackVertexKineticEnergy'] * 1000  # MeV to KeV
    hist, bins = np.histogram(data, range=(data_ref.min(), data_ref.max()),
                              bins=100, density=False)
    """ax2.hist(data, bins=100, density=False,
             range=(data_ref.min(), data_ref.max()), histtype='stepfilled', alpha=0.5,
             label=f'{rads[i]}', color='b')"""
    # differences
    mean = hist_ref.sum() / len(hist_ref)
    msad = np.sum(np.abs(np.subtract(hist_ref, hist))) / len(hist_ref) / mean * 100
    t = msad < tol
    gam.print_test(t, f'Mean bin difference for {rad} is {msad:.2f}% (tol is {tol}%)')
    is_ok = is_ok and t

gam.test_ok(is_ok)
