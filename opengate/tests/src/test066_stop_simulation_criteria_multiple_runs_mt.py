#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 15:00:21 2024

@author: fava
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
import itk
import numpy as np


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

    # check statistical uncertainty every n_check simulated particles
    n_planned = 650000
    n_threads = 1
    n_runs = 4

    # goal uncertainty
    unc_goal_run = 0.05
    unc_expected = unc_goal_run / np.sqrt(
        n_runs
    )  # uncertainty expected at the end of the simulation
    thresh_voxel_edep_for_unc_calc = (
        0.7  # calculated over the voxels whose value is > 0.7 * max edep value
    )

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
    dose.output_filename = "test066-edep.mhd"
    dose.attached_to = "waterbox"
    dose.size = [40, 40, 40]
    mm = gate.g4_units.mm
    dose.spacing = [2.5 * mm, 2.5 * mm, 2.5 * mm]
    dose.edep_uncertainty.active = True
    dose.edep.keep_data_per_run = True
    dose.uncertainty_goal = unc_goal_run
    dose.uncertainty_first_check_after_n_events = 100
    dose.uncertainty_voxel_edep_threshold = thresh_voxel_edep_for_unc_calc
    dose.write_to_disk = False  # we don't need to save the images for this test

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    stat.write_to_disk = False

    # start simulation
    lower = np.arange(0, 1, 1 / n_runs) * sec
    upper = lower + 1 / n_runs * sec
    sim.run_timing_intervals = list(zip(lower, upper))
    sim.run()

    # print results at the end
    print(stat)

    ok = True
    # test that the uncertainty goal was met in each run:
    for i in range(len(sim.run_timing_intervals)):
        edep_arr = np.asarray(dose.edep.get_data(which=i))
        unc_arr = np.asarray(dose.edep_uncertainty.get_data(which=i))
        unc_mean = calculate_mean_unc(
            edep_arr, unc_arr, edep_thresh_rel=thresh_voxel_edep_for_unc_calc
        )
        b = unc_mean < unc_goal_run
        print(
            f"For run index {i}: \n"
            f"    mean uncertainty = {unc_mean}, "
            f"    goal = {unc_goal_run}"
            f"    OK? -> {b}"
        )
        ok &= b

    # Test that mean uncertainty satisfies the goal uncertainty
    # in the edep image merged over the runs
    # The goal might not be strictly met
    # because the voxels over which the uncertainty is calculated are not strictly the same
    # because they are threshold-based
    # Therefore, we allow some margin around the goal
    test_thresh_rel = 0.01

    edep_arr = np.asarray(dose.edep.image)
    unc_array = np.asarray(dose.edep_uncertainty.image)

    unc_mean = calculate_mean_unc(
        edep_arr, unc_array, edep_thresh_rel=thresh_voxel_edep_for_unc_calc
    )
    print(f"{unc_expected = }")
    print(f"{unc_mean = }")
    ok &= (
        unc_mean < unc_expected + test_thresh_rel
        and unc_mean > unc_expected - test_thresh_rel
    )
    print("OK? -> ", ok)

    # test that the simulation stopped because of the threshold crtierion,
    # and not simply because we reached the planned number of events
    n_planned = n_planned * n_threads
    n_effective = stat.counts.events
    print(f"{n_planned = }")
    print(f"{n_effective = }")
    b = n_effective < n_planned
    print("OK? -> ", b)
    ok = ok and b

    utility.test_ok(ok)
