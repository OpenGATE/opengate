#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
import opengate as gate
from matplotlib import pyplot as plt

from opengate import g4_units
from opengate.tests.utility import get_image_1d_profile, print_test


def add_waterbox(sim):
    # units
    cm = gate.g4_units.cm

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [30 * cm, 30 * cm, 20 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # low density box
    low_density_box = sim.add_volume("Box", "low_density_box")
    low_density_box.mother = waterbox.name
    low_density_box.size = [30 * cm, 30 * cm, 3 * cm]
    low_density_box.translation = [0 * cm, 0 * cm, -6 * cm]
    low_density_box.material = "G4_lPROPANE"  # density is around 0.43
    low_density_box.color = [0, 1, 1, 1]

    # high density box
    high_density_box = sim.add_volume("Box", "high_density_box")
    high_density_box.mother = waterbox.name
    high_density_box.size = [30 * cm, 30 * cm, 1 * cm]
    high_density_box.translation = [0 * cm, 0 * cm, 1 * cm]
    high_density_box.material = "G4_Pyrex_Glass"  # density is around 2.23
    high_density_box.color = [1, 0, 0, 1]

    return waterbox


def add_simple_waterbox(sim):
    # units
    cm = gate.g4_units.cm

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.size = [30 * cm, 30 * cm, 30 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]
    return waterbox


def add_source(
    sim,
    n=1e5,
    energy=350 * g4_units.keV,
    sigma=0.3 * g4_units.MeV,
    radius=3 * g4_units.cm,
):
    cm = gate.g4_units.cm
    source = sim.add_source("GenericSource", "source")
    source.energy.mono = energy
    source.energy.type = "gauss"
    source.energy.sigma_gauss = sigma
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = radius
    source.position.translation = [0, 0, -55 * cm]
    source.direction.type = "focused"
    source.direction.focus_point = [0, 0, -20 * cm]
    source.n = n / sim.number_of_threads
    if sim.visu:
        source.n = 10
    return source


def add_iso_source(
    sim,
    n=1e5,
    energy=2 * g4_units.MeV,
    sigma=0.6 * g4_units.MeV,
):
    cm = gate.g4_units.cm
    source = sim.add_source("GenericSource", "source")
    source.energy.mono = energy
    source.energy.type = "gauss"
    source.energy.sigma_gauss = sigma
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 10 ** (-7) * cm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.n = n / sim.number_of_threads
    if sim.visu:
        source.n = 100
    return source


def voxelize_waterbox(sim, output_folder):
    mm = gate.g4_units.mm
    a = sim.output_dir
    sim.output_dir = output_folder
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_8mm", spacing=(8 * mm, 8 * mm, 8 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_5mm", spacing=(5 * mm, 5 * mm, 5 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_3mm", spacing=(3 * mm, 3 * mm, 3 * mm)
    )
    sim.voxelize_geometry(
        filename="waterbox_with_inserts_1mm", spacing=(1 * mm, 1 * mm, 1 * mm)
    )
    sim.output_dir = a


def plot_pdd(dose_actor, tle_dose_actor, offset=(0, 0)):
    # plot pdd
    fig, ax = plt.subplots(ncols=2, nrows=1, figsize=(13, 5))

    a = ax[0]
    pdd_x, pdd_y = get_image_1d_profile(
        dose_actor.edep.get_output_path(), "z", offset=offset
    )
    a.plot(pdd_x, pdd_y, label="edep analog")
    pdd_x, pdd_y = get_image_1d_profile(
        tle_dose_actor.edep.get_output_path(), "z", offset=offset
    )
    a.plot(pdd_x, pdd_y, label="edep TLE")
    a.set_xlabel("distance [mm]")
    a.set_ylabel("edep [MeV]")
    a.legend()

    a = a.twinx()
    pdd_x, pdd_y = get_image_1d_profile(
        dose_actor.dose_uncertainty.get_output_path(), "z", offset=offset
    )
    a.plot(
        pdd_x,
        pdd_y,
        label="uncert analog",
        linestyle="--",
        linewidth=0.5,
        color="lightseagreen",
    )
    pdd_x, pdd_y = get_image_1d_profile(
        tle_dose_actor.dose_uncertainty.get_output_path(), "z", offset=offset
    )
    a.plot(
        pdd_x,
        pdd_y,
        label="uncert TLE",
        linestyle="--",
        linewidth=0.5,
        color="darkorange",
    )
    a.legend()

    a = ax[1]
    pdd_x, pdd_y = get_image_1d_profile(
        dose_actor.dose.get_output_path(), "z", offset=offset
    )
    a.plot(pdd_x, pdd_y, label="dose analog")
    pdd_x, pdd_y = get_image_1d_profile(
        tle_dose_actor.dose.get_output_path(), "z", offset=offset
    )
    a.plot(pdd_x, pdd_y, label="dose TLE")
    a.set_xlabel("distance [mm]")
    a.set_ylabel("dose [Gy]")
    a.legend()

    return ax, plt


def mean_rel_diff(arr1, arr2, i1, i2, spacing, ax, tol):
    v1 = arr1[i1:i2].mean()
    v2 = arr2[i1:i2].mean()
    r = np.fabs(v1 - v2) / v1
    b = r < tol
    print_test(
        b,
        f"Relative difference {i1} {i2} {v1:.3f} vs {v2:.3f} "
        f"= {r * 100:.2f}% (tol={tol*100:.0f}) ==> {b}",
    )

    # plot
    ax.plot((i1 * spacing, i2 * spacing), (v1, v1), color="darkgray")
    ax.plot((i1 * spacing, i2 * spacing), (v2, v2), color="black")

    return b


def compare_pdd(f1, f2, spacing, ax, tol, offset=0):
    img1 = itk.imread(f1)
    img2 = itk.imread(f2)
    img1_arr = itk.GetArrayFromImage(img1)
    img2_arr = itk.GetArrayFromImage(img2)
    s = img1_arr.shape
    img1_arr = img1_arr[:, int(s[1] / 2), int(s[2] / 2) + offset]
    img2_arr = img2_arr[:, int(s[1] / 2), int(s[2] / 2) + offset]

    # param of the box
    cm = gate.g4_units.cm
    wbs = 20 * cm  # waterbox size
    ldp = 6 * cm  # low density size
    lds = 3 * cm  # low density position
    hdp = 1 * cm  # high density size
    hds = 1 * cm  # high density position

    # entrance section (water)
    w = int(((-ldp - lds / 2) - (-wbs / 2)) / spacing)
    b = mean_rel_diff(img1_arr, img2_arr, 0, w, spacing, ax, tol)

    # low density section
    l = int(lds / spacing)
    b = mean_rel_diff(img1_arr, img2_arr, w, w + l, spacing, ax, tol) and b

    # water section
    w2 = int(((hdp - hds / 2) - (-ldp + lds / 2)) / spacing)
    a = w + l + w2
    b = mean_rel_diff(img1_arr, img2_arr, w + l, a, spacing, ax, tol) and b

    # high density section
    h = int(hds / spacing)
    b = mean_rel_diff(img1_arr, img2_arr, a, a + h, spacing, ax, tol * 3) and b

    return b
