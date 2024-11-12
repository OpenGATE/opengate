#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
import itk
import numpy as np


# WARNING: This test does currently not work correctly
# because the tested functionality od the dose actor is currently not available
# Test should be successful, but that is meaningless


def define_run_timing_intervals(n):
    sec = gate.g4_units.second
    start = 0
    end = 1 * sec / n
    run_timing_intervals = []
    for r in range(n):
        run_timing_intervals.append([start, end])
        start = end
        end += 1 * sec / n

    return run_timing_intervals


def calculate_mean(edep_arr, unc_arr, edep_thresh_rel=0.7):
    edep_max = np.amax(edep_arr)
    mask = edep_arr > edep_max * edep_thresh_rel
    unc_used = unc_arr[mask]
    unc_mean = np.mean(unc_used)

    return unc_mean


def run_simulation(n_runs, n_part_tot, n_threads, uncertainty_type="uncertainty"):
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test066"
    )

    run_timing_intervals = define_run_timing_intervals(n_runs)

    print(f"--- N runs: {len(run_timing_intervals)* n_threads}")

    n_part_thread = int(n_part_tot / n_threads)

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 983456
    sim.number_of_threads = n_threads
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

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
    source.n = n_part_thread  # 1 part/s

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test066-edep.mhd"
    dose.attached_to = waterbox
    dose.size = [40, 40, 40]
    mm = gate.g4_units.mm
    dose.spacing = [2.5 * mm, 2.5 * mm, 2.5 * mm]
    if uncertainty_type == "uncertainty":
        dose.edep_uncertainty.active = True
        # dose.ste_of_mean = False  # currently not available
    elif uncertainty_type == "ste_of_mean":
        dose.edep_uncertainty.active = False
        # dose.ste_of_mean = True  # currently not available

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    stat.output_filename = "stats066.txt"

    # motion
    sim.run_timing_intervals = run_timing_intervals

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stat)

    print(dose)

    # edep_path = dose.edep.get_output_path()
    # unc_path = dose.edep_uncertainty.get_output_path()

    # test that the simulation didn't stop because we reached the planned number of runs
    stats_ref = utility.read_stat_file(paths.output / "stats066.txt")
    n_runs_planned = len(run_timing_intervals) * n_threads
    n_effective_runs = stats_ref.counts.runs
    print(f"{n_runs_planned = }")
    print(f"{n_effective_runs = }")

    return dose.edep.get_data(), dose.edep_uncertainty.get_data()
    # return itk.imread(str(edep_path)), itk.imread(str(unc_path))


if __name__ == "__main__":
    n_part_tot = 10000
    ok = True
    # Uncertainty
    edep_ref, unc_ref = run_simulation(
        n_runs=1, n_part_tot=n_part_tot, n_threads=1, uncertainty_type="uncertainty"
    )
    edep_test, unc_test = run_simulation(
        n_runs=10, n_part_tot=n_part_tot, n_threads=1, uncertainty_type="uncertainty"
    )
    print("------- test uncertainty for multiple runs -------")
    ok = (
        utility.assert_images_ratio_per_voxel(
            1, edep_test, edep_ref, abs_tolerance=0.03, mhd_is_path=False
        )
        and ok
    )
    ok = (
        utility.assert_images_ratio_per_voxel(
            1, unc_test, unc_ref, abs_tolerance=0.03, mhd_is_path=False
        )
        and ok
    )

    # STE of mean
    edep_ref, unc_ref = run_simulation(
        n_runs=1, n_part_tot=n_part_tot, n_threads=10, uncertainty_type="ste_of_mean"
    )
    edep_test, unc_test = run_simulation(
        n_runs=10, n_part_tot=n_part_tot, n_threads=10, uncertainty_type="ste_of_mean"
    )
    print("------- test ste_of_mean for multiple runs -------")
    ok = (
        utility.assert_images_ratio_per_voxel(
            1, edep_test, edep_ref, abs_tolerance=0.03, mhd_is_path=False
        )
        and ok
    )
    ok = (
        utility.assert_images_ratio_per_voxel(
            1, unc_test, unc_ref, abs_tolerance=0.03, mhd_is_path=False
        )
        and ok
    )

    utility.test_ok(ok)
