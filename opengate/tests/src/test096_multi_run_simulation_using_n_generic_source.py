#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
import numpy as np
import uproot


def is_ok_test096(rootfile_1, rootfile_2, time_intervals, nb_run, nb_part):
    time_1 = rootfile_1["GlobalTime"] - rootfile_1["LocalTime"]
    time_2 = rootfile_2["GlobalTime"] - rootfile_2["LocalTime"]
    bool_source_1 = False
    bool_source_2 = False
    count_true_source_1 = 0

    print("For activity source :")
    for i in range(nb_run):
        tmp_time = time_1[
            (time_1 >= time_intervals[i][0]) & (time_1 < time_intervals[i][1])
        ]
        err_count = np.sqrt(len(tmp_time))
        if len(tmp_time) - 4 * err_count <= nb_part <= len(tmp_time) + 4 * err_count:
            count_true_source_1 += 1
        err_time = np.std(tmp_time, ddof=1)
        theo_err = (time_intervals[i][1] - time_intervals[i][0]) / np.sqrt(12)
        if (
            err_time - 4 * err_time / err_count
            <= theo_err
            <= err_time + 4 * err_time / err_count
        ):
            count_true_source_1 += 1

        print(f"Theoretical number of particle in run_{i}:", nb_part)
        print(
            f"Experimental number of particle in run_{i}: {len(tmp_time)} +- {err_count}"
        )
        print(f"Theoretical std.dev in run_{i}: {theo_err/10**9} ns")
        print(
            f"Experimental std.dev in run_{i}: {err_time/10**9} ns +- {err_time / err_count/10**9}"
        )

    count_true_source_2 = 0
    print("")
    print("For n source :")
    for i in range(nb_run):
        tmp_time = time_2[
            (time_2 >= time_intervals[i][0]) & (time_2 < time_intervals[i][1])
        ]

        if np.all(tmp_time == time_intervals[i][0]) and len(tmp_time) == nb_part:
            count_true_source_2 += 1

        print(f"Theoretical number of particle in run_{i}:", nb_part)
        print(f"Experimental number of particle in run_{i}: {len(tmp_time)}")
    if count_true_source_2 == 5:
        bool_source_1 = True
    if count_true_source_1 == 10:
        bool_source_2 = True

    return bool_source_1 and bool_source_2


def add_source(n, type, z_dir):
    Bq = gate.g4_units.Bq
    source = sim.add_source("GenericSource", f"mysource_{type}")
    source.energy.mono = 150 * MeV
    source.particle = "gamma"
    source.position.type = "disc"
    source.position.radius = 5 * nm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, z_dir]
    if type == "activity":
        source.activity = n * Bq
    if type == "n":
        source.n = n


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test096", "test096")

    # create the simulation
    sim = gate.Simulation()
    ui = sim.user_info
    ui.running_verbose_level = gate.logger.RUN

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = "auto"
    sim.output_dir = paths.output
    nb_run = 5

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    #  change world size
    sim.world.size = [20 * cm, 20 * cm, 20 * cm]
    sim.world.material = "G4_Galactic"

    # add a simple fake volume to test hierarchy

    # physics
    sim.physics_manager.set_production_cut("world", "all", 1000 * m)
    nb_part = 1000
    add_source(nb_part, "activity", 1)
    add_source(np.zeros(nb_run) + nb_part, "n", -1)

    sim.run_timing_intervals = []
    for i in range(5):
        sim.run_timing_intervals.append([i * sec, (i + 1) * sec])

    l_names = ["plan_1", "plan_2"]
    l_phsp = []
    for i, name in enumerate(l_names):
        plan = sim.add_volume("Box", name)
        plan.size = [2 * cm, 2 * cm, 1 * nm]
        if i == 0:
            z = 5 * cm
        else:
            z = -5 * cm
        plan.translation = [0, 0, z]
        plan.material = "G4_Galactic"
        ta = sim.add_actor("PhaseSpaceActor", f"PhaseSpace_{name}")
        ta.attached_to = plan.name
        ta.attributes = [
            "GlobalTime",
            "LocalTime",
        ]
        ta.output_filename = f"test096_hits_{name}.root"
        l_phsp.append(ta)

    # add dose actor

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    sim.run()
    print(stats)

    l_arr = []
    for i, phsp in enumerate(l_phsp):
        with uproot.open(phsp.get_output_path()) as f_phsp:
            arr = f_phsp[f"PhaseSpace_plan_{i+1}"].arrays()
            l_arr.append(arr)

    is_ok = is_ok_test096(l_arr[0], l_arr[1], sim.run_timing_intervals, nb_run, nb_part)
    utility.test_ok(is_ok)
