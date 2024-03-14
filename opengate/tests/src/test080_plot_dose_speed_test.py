#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import matplotlib
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset
import numpy as np
import json

from test080_dose_speed_test_helpers import create_label, test_paths

matplotlib.style.use("ggplot")


def get_color_from_key(k):
    if "local" in k:
        return "C1"
    elif "standard" in k:
        return "k"
    elif "pointer" in k:
        return "C0"
    elif "atomic" in k:
        return "C5"


def get_marker_from_key(k):
    if "local" in k:
        return "s"
    elif "standard" in k:
        return "o"
    elif "pointer" in k:
        return "v"
    elif "atomic" in k:
        return "^"


def plot_results(which):
    filename = test_paths.output / f"results_doseactor_speed_comparison_{which}.json"
    n_primaries_list = [1e3, 1e4]  # , 1e5, 1e6]
    plt.figure(figsize=(7, 5))
    ax = plt.gca()
    axins = zoomed_inset_axes(
        ax, 8, loc="upper left", axes_kwargs={"frame_on": True}
    )  # zoom = 6
    with open(filename, "r") as fp:
        scenarios = json.load(fp)
        marker_size = 20
        for k, s in scenarios.items():
            if s["number_of_threads"] == 1:
                ls = "--"
            else:
                ls = "-"
            # s['n_primaries_list']
            color = get_color_from_key(k)
            marker = get_marker_from_key(k)
            (l,) = ax.plot(
                s["n_primaries_list"],
                s["sim_times"],
                label=create_label(s),
                color=color,
                linestyle=ls,
            )
            ax.scatter(
                s["n_primaries_list"],
                s["sim_times"],
                s=marker_size,
                marker=marker,
                color=l.get_color(),
                alpha=0.5,
            )
            axins.plot(
                s["n_primaries_list"], s["sim_times"], color=l.get_color(), linestyle=ls
            )
            axins.scatter(
                s["n_primaries_list"],
                s["sim_times"],
                s=marker_size,
                marker=marker,
                color=l.get_color(),
                alpha=0.5,
            )
            marker_size *= 1.2

    axins.yaxis.set_ticklabels([])
    plt.ticklabel_format(axis="x", style="sci", scilimits=(0, 0))
    axins.set_xlim([0.05 * v for v in ax.get_xlim()])
    axins.set_ylim([0.05 * v for v in ax.get_ylim()])
    mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.5")

    for pos in ["top", "bottom", "right", "left"]:
        axins.spines[pos].set_edgecolor("k")
        axins.spines[pos].set(linewidth=0.5)

    ax.set_xlabel("Number of primaries")
    ax.set_ylabel("Simulation time in s")

    ax.legend(loc=(0, 1.02), fontsize="xx-small")

    plt.tight_layout()
    plt.show()
    plt.savefig(test_paths.output / f"dose_actor_speed_test_{which}.pdf")
    plt.savefig(test_paths.output / f"dose_actor_speed_test_{which}.png", dpi=300)


if __name__ == "__main__":
    plot_results("small")
    plot_results("large")
    plot_results("single")
