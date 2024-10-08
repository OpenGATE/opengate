#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
import itk
import numpy as np


def define_run_timing_intervals(
    n_part_per_core, n_part_check, n_threads, skip_first_n_part=0, n_last_run=1000
):
    sec = gate.g4_units.second
    n_tot_planned = n_part_per_core * n_threads
    if skip_first_n_part == 0:
        run_timing_intervals = []
        start_0 = 0
    else:
        run_timing_intervals = [[0, (skip_first_n_part / n_tot_planned) * sec]]
        start_0 = (skip_first_n_part / n_tot_planned) * sec

    end_last = (n_last_run / n_tot_planned) * sec
    n_runs = round(((n_tot_planned - skip_first_n_part - n_last_run) / n_part_check))
    # print(n_runs)

    # end = start + 1 * sec / n_runs
    end = start_0 + (1 * sec - start_0 - end_last) / n_runs
    start = start_0
    for r in range(n_runs):
        run_timing_intervals.append([start, end])
        start = end
        end += (1 * sec - start_0 - end_last) / n_runs

    run_timing_intervals.append([start, start + end_last])
    # print(run_timing_intervals)

    return run_timing_intervals


def calculate_mean_unc(edep_arr, unc_arr, edep_thresh_rel=0.7):
    edep_max = np.amax(edep_arr)
    mask = edep_arr > edep_max * edep_thresh_rel
    unc_used = unc_arr[mask]
    unc_mean = np.mean(unc_used)

    return unc_mean


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test066"
    )

    # check statistical uncertainty every n_check simlated particles
    n_planned = 650000
    n_check = 3000
    n_threads = 16
    # n_runs = round(n_planned*n_threads/(n_check))
    run_timing_intervals = define_run_timing_intervals(
        n_planned, n_check, n_threads, skip_first_n_part=11000
    )

    # goal uncertainty
    unc_goal = 0.03
    thresh_voxel_edep_for_unc_calc = 0.7

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 983456
    sim.number_of_threads = n_threads

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
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", -20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.set_production_cut("world", "all", 700 * um)

    # default source for tests
    # the source is fixed at the center, only the volume will move
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 90 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 5 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = n_planned * Bq  # 1 part/s

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = paths.output / "test066-edep.mhd"
    dose.attached_to = "waterbox"
    dose.size = [40, 40, 40]
    mm = gate.g4_units.mm
    dose.spacing = [2.5 * mm, 2.5 * mm, 2.5 * mm]
    dose.uncertainty = False
    dose.ste_of_mean = True
    # dose.use_more_ram = True
    dose.goal_uncertainty = unc_goal
    dose.thresh_voxel_edep_for_unc_calc = thresh_voxel_edep_for_unc_calc

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True
    s.output = paths.output / "stats066.txt"

    # motion
    sim.run_timing_intervals = run_timing_intervals

    # start simulation
    sim.run()
    output = sim.output

    # print results at the end
    stat = output.get_actor("Stats")
    print(stat)

    dose = output.get_actor("dose")
    print(dose)

    # test that final mean uncertainty satisfies the goal uncertainty
    test_thresh_rel = 0.01
    d = output.get_actor("dose")

    edep_img = itk.imread(paths.output / d.user_info.output)
    edep_arr = itk.GetArrayViewFromImage(edep_img)
    unc_img = itk.imread(paths.output / d.user_info.output_uncertainty)
    unc_array = itk.GetArrayFromImage(unc_img)

    unc_mean = calculate_mean_unc(
        edep_arr, unc_array, edep_thresh_rel=thresh_voxel_edep_for_unc_calc
    )
    print(f"{unc_goal = }")
    print(f"{unc_mean = }")
    ok = unc_mean < unc_goal and unc_mean > unc_goal - test_thresh_rel

    # test that the simulation didn't stop because we reached the planned number of runs
    stats_ref = utility.read_stat_file(paths.output / "stats066.txt")
    n_runs_planned = len(run_timing_intervals) * n_threads
    n_effective_runs = stats_ref.counts.runs
    print(f"{n_runs_planned = }")
    print(f"{n_effective_runs = }")
    ok = ok and n_effective_runs < n_runs_planned

    utility.test_ok(ok)
