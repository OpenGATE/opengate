#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.sources.phidsources as phidsources
import click
import numpy as np
import matplotlib.pyplot as plt
import radioactivedecay as rd
from opengate.utility import g4_best_unit

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("rad_name", nargs=1)
@click.option("--output", "-o", default=None, help="output file")
@click.option("--verbose", "-v", is_flag=True, default=False, help="verbose")
@click.option(
    "--log_scale", "--log", is_flag=True, default=False, help="plot with log scale"
)
@click.option("--start_h", default=24.0, help="time start in hour")
@click.option("--duration_s", default=200.0, help="duration in sec")
@click.option("--n_first", "-n", default=10, help="print n largest weights")
@click.option(
    "--half_life", default=None, type=float, help="Specify the half-life for metastable"
)
@click.option(
    "--half_life_unit",
    default=None,
    help="Specify the half-life unit for metastable us, s, h etc",
)
def go(
    rad_name,
    output,
    verbose,
    log_scale,
    start_h,
    duration_s,
    n_first,
    half_life,
    half_life_unit,
):
    """
    Display all gammas (isomeric transition + atomic relaxation) for a radionuclide with all its decay chains.
    The relative activities of the daughters radionuclides are computed according to start+duration timing.

    For metastable, you can set the half-life.

    """

    # get nuclide, a, z
    nuclide = phidsources.get_nuclide_from_name(rad_name)
    name = nuclide.nuclide[: nuclide.nuclide.index("-")]

    # get all daughters
    daughters = phidsources.get_nuclide_progeny(nuclide)
    if verbose:
        print(
            f"Found {len(daughters)} daughters for {name} HL={nuclide.half_life('m')} min"
        )

    # TAC
    inv = rd.Inventory({nuclide.nuclide: 1.0}, "Bq")
    inv = inv.decay(start_h, "h")
    if verbose:
        for a in inv.activities():
            print(f"{a} {inv.activities()[a] * 100:.2f}%")

    ca = inv.cumulative_decays(duration_s, "s")
    for n in ca:
        ca[n] /= duration_s
    if verbose:
        for a in inv.activities():
            print(f"{a} {inv.activities()[a] * 100:.2f}%")

    # Isomeric transition
    sec = gate.g4_units.s
    us = gate.g4_units.us
    hour = gate.g4_units.h
    if half_life is None:
        it = phidsources.isomeric_transition_load_all_gammas(nuclide)
        half_life = nuclide.half_life("s") * sec
    else:
        unit = gate.g4_units[half_life_unit]
        hl = half_life * unit
        print(f"Half life is {g4_best_unit(hl, 'Time')}")
        it = phidsources.isomeric_transition_load_all_gammas(nuclide, half_life=hl)

    # Atomic relaxation
    ar = phidsources.atomic_relaxation_load_all_gammas(nuclide)

    # merge both
    all = it + ar

    # take tac into account
    for x in all:
        n = x["nuclide"].nuclide.nuclide
        if n in ca:
            p = ca[n]
            x["intensity"] *= p
        else:
            x["intensity"] = 0

    # prepare to sort
    w_all = np.array([w["intensity"] for w in all])
    ene_all = np.array([w["energy"] for w in all])
    t_all = np.array([w["type"] for w in all])
    n_all = np.array([w["nuclide"] for w in all])

    # sort by weights
    sorted_indices = np.argsort(-w_all)
    sorted_weights = w_all[sorted_indices]
    sorted_ene = ene_all[sorted_indices]
    sorted_types = t_all[sorted_indices]
    sorted_nuc = n_all[sorted_indices]

    # print
    keV = gate.g4_units.keV
    i = 0
    n = n_first
    if verbose:
        print(f"Number of IT = {len(it)} and of AR = {len(ar)}")
        for e, w, t, nuc in zip(
            sorted_ene[:n], sorted_weights[:n], sorted_types[:n], sorted_nuc[:n]
        ):
            print(
                f"{i} Energy {e / keV:.3f} keV     {w * 100:.3f} %  {t} {nuc.nuclide.nuclide}"
            )
            i += 1

    # plot
    SIZE = 14
    fig, ax = plt.subplots(1, 1, figsize=(15, 5))
    color_mapping = {"it": "red", "ar": "blue"}
    colors = [color_mapping[val] for val in sorted_types]
    w = (sorted_ene.max() - sorted_ene.min()) / 300
    print(f"Max energy = {sorted_ene.max() / keV} keV")
    ax.bar(
        sorted_ene / keV,
        sorted_weights * 100,
        width=w / keV,
        color=colors,
        log=log_scale,
    )
    l = len(sorted_ene)

    # Add text annotations for the three largest bars
    for i in range(0, n_first):
        energy = sorted_ene[i] / keV
        w = sorted_weights[i] * 100
        n = sorted_nuc[i].nuclide.nuclide
        text = f"{energy:.1f} keV\n{w:.1f}% \n {n}"
        plt.annotate(
            text,
            xy=(energy, w),
            xytext=(energy, w),
            ha="center",
            va="bottom",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"),
        )

    ax.set_xlabel("Energy keV", fontsize=SIZE)
    ax.set_ylabel("Intensity %", fontsize=SIZE)
    plt.xticks(fontsize=SIZE)
    plt.yticks(fontsize=SIZE)

    x_range = ax.get_xlim()
    y_range = ax.get_ylim()
    x = (x_range[1] - x_range[0]) / 5 * 3.5 + x_range[0]
    y = (y_range[1] - y_range[0]) / 2 + y_range[0]
    plt.annotate(
        f"{nuclide.nuclide}\n"
        f"Half-life = {g4_best_unit(half_life, 'Time')}\n"
        f"at t={g4_best_unit(start_h * hour, 'Time')}\n"
        f"{l} photon sources \n",
        xy=(x, y),
        fontsize=SIZE,
    )
    # ax.legend()

    if output:
        print(f"Output plot in {output}")
        fig.savefig(output)
    else:
        plt.show()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
