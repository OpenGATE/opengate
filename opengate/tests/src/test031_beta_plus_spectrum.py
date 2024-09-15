#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np
import uproot

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test031")

    l = gate.sources.generic.all_beta_plus_radionuclides
    # l = ['F18', 'Ga68', 'O15']
    # l = ['F18']

    # references (02/2022)
    # http://www.lnhb.fr/nuclear-data/module-lara/
    rad_yields = {
        "F18": 0.968600992766,
        "Ga68": 0.8883814158496728,
        "Zr89": 0.22799992881708,
        "Na22": 0.8972935562750121,
        "C11": 0.9974862363857401,
        "N13": 0.9981749688051,
        "O15": 0.9988401691350001,
        "Rb82": 0.95410853035736,
    }

    # Get one color for each rad
    fig, ax1 = plt.subplots(1, 1, figsize=(20, 10))
    cmap = plt.get_cmap("Dark2")
    rad_color = {}
    n = len(l)
    i = 0
    for rad in l:
        rad_color[rad] = cmap(i / n)
        i += 1

    for rad in l:
        data = gate.sources.generic.read_beta_plus_spectra(rad)
        x = data[:, 0]  # energy E(keV)
        y = data[:, 1]  # proba  dNtot/dE b+
        # normalize taking into account the bins density
        dx = gate.sources.generic.compute_bins_density(x)
        s = (y * dx).sum()
        y = y / s
        ax1.plot(x, y, label=rad, color=rad_color[rad])

    plt.xlabel("Energy KeV")
    plt.ylabel("Probability")
    ax1.legend()
    plt.text(2200, 0.0023, "BetaShape")
    plt.text(2200, 0.0020, "Mougeot, Phys Rev C 91, 055504 (2015)")
    plt.text(2200, 0.0017, "http://www.lnhb.fr/nuclear-data/module-lara")

    # units
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    Bq = gate.g4_units.Bq

    # simulation
    sim = gate.Simulation()
    sim.visu = False
    sim.random_seed = 123456
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"
    sim.output_dir = paths.output

    def add_box(i):
        b = sim.add_volume("Box", f"b{i}")
        b.size = [1 * cm, 1 * cm, 1 * cm]
        b.translation = [2 * i * cm, 0 * cm, 0 * cm]
        b.material = "G4_Galactic"

    tol = 0.03

    def add_source(rad):
        si = len(rads)
        add_box(si)
        source = sim.add_source("GenericSource", f"source_{rad}")
        source.mother = f"b{si}"
        source.particle = "e+"
        source.energy.type = f"{rad}"
        source.position.type = "point"
        source.direction.type = "iso"
        """
            WARNING
            with real simulation, the activity should be weighted by the total yield !
        """
        total_yield = gate.sources.generic.get_rad_yield(rad)
        source.activity = activity  # * total_yield  <--- this should be taken into account in real simulation
        yi = rad_yields[rad]
        t = (total_yield - yi) / yi < tol
        utility.print_test(
            t, f"Rad {rad} total yield = {total_yield} vs {yi} (tol is {tol})"
        )

        phsp = sim.add_actor("PhaseSpaceActor", f"phsp_{rad}")
        phsp.attached_to = f"b{si}"
        phsp.attributes = ["TrackVertexKineticEnergy"]
        phsp.output_filename = f"test031_{rad}.root"
        phsp.steps_to_store = "exiting"
        f = sim.add_filter("ParticleFilter", f"f_{rad}")
        f.particle = "e+"
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

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.run()

    # print results
    print(stats)

    # plot
    for i in range(len(rads)):
        rad = rads[i]
        data = uproot.open(sim.get_actor(f"phsp_{rad}").get_output_path())[
            f"phsp_{rad}"
        ]
        data = (
            data.arrays(library="numpy")["TrackVertexKineticEnergy"] * 1000
        )  # MeV to KeV
        ax1.hist(
            data,
            bins=200,
            density=True,
            histtype="stepfilled",
            alpha=0.5,
            label=f"{rads[i]}",
            color=rad_color[rad],
        )

    f = paths.output / "test031.png"
    ax1.legend(loc="upper center")
    plt.savefig(f)
    print(f"Figure save in {f}")

    # compute diff
    # ax2 = ax1.twinx()
    is_ok = True
    tol = 4.1
    for rad in rads:
        # input
        output = paths.output_ref / f"test031_{rad}.root"
        data_ref = uproot.open(output)[f"phsp_{rad}"]
        data_ref = (
            data_ref.arrays(library="numpy")["TrackVertexKineticEnergy"] * 1000
        )  # MeV to KeV
        hist_ref, bins_ref = np.histogram(
            data_ref, range=(data_ref.min(), data_ref.max()), bins=100, density=False
        )
        """ax2.hist(data_ref, bins=100, density=False,
                 range=(data_ref.min(), data_ref.max()), histtype='stepfilled',
                 alpha=0.5, label=f'{rads[i]}', color='r')"""
        # output
        output = paths.output / f"test031_{rad}.root"
        data = uproot.open(output)[f"phsp_{rad}"]
        data = (
            data.arrays(library="numpy")["TrackVertexKineticEnergy"] * 1000
        )  # MeV to KeV
        hist, bins = np.histogram(
            data, range=(data_ref.min(), data_ref.max()), bins=100, density=False
        )
        """ax2.hist(data, bins=100, density=False,
                 range=(data_ref.min(), data_ref.max()), histtype='stepfilled', alpha=0.5,
                 label=f'{rads[i]}', color='b')"""
        # differences
        mean = hist_ref.sum() / len(hist_ref)
        msad = np.sum(np.abs(np.subtract(hist_ref, hist))) / len(hist_ref) / mean * 100
        t = msad < tol
        utility.print_test(
            t, f"Mean bin difference for {rad} is {msad:.2f}% (tol is {tol}%)"
        )
        is_ok = is_ok and t

    utility.test_ok(is_ok)
