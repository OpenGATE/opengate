#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektaversa as versa
import opengate.contrib.linacs.dicomrtplan as rtplan
from opengate.tests import utility
from opengate.utility import g4_units
from scipy.spatial.transform import Rotation
import numpy as np
import itk


def calc_mlc_aperture(x_leaf_position, y_jaws_position):

    left = x_leaf_position[:80]
    right = x_leaf_position[80:]
    proj_leaves_y = np.arange(-40 * 5 + 2.5, 40 * 5 - 2.5 + 0.1, 5)

    left[
        (proj_leaves_y - 2.5 < y_jaws_position[0])
        | (proj_leaves_y + 2.5 > y_jaws_position[1])
    ] = 0
    right[
        (proj_leaves_y - 2.5 < y_jaws_position[0])
        | (proj_leaves_y + 2.5 > y_jaws_position[1])
    ] = 0
    diff = np.array(np.abs(right - left)) * 5

    return np.sum(diff)


def add_volume_to_irradiate(sim, name, l_cp):
    mm = g4_units.mm
    m = g4_units.m
    plane = sim.add_volume("Box", "water_plane")
    plane.mother = name
    plane.material = "G4_WATER"
    plane.size = [0.4 * m, 0.4 * m, 2 * cm]
    plane.translation = [0 * mm, 0 * mm, -1 * cm]
    plane.color = [1, 0, 0, 1]  # red

    voxel_size_x = 1.2 * mm
    voxel_size_y = 1.2 * mm
    voxel_size_z = 2 * cm

    dim_box = [
        plane.size[0] / voxel_size_x,
        plane.size[1] / voxel_size_y,
        1,
    ]
    dose = sim.add_actor("DoseActor", "dose_water_slice")
    dose.attached_to = plane
    dose.edep.output_filename = "dose_actor_versa_rt_plan.mhd"  # FIXME
    dose.size = [int(dim_box[0]), int(dim_box[1]), int(dim_box[2])]
    dose.spacing = [voxel_size_x, voxel_size_y, voxel_size_z]
    dose.hit_type = "random"

    # move the plane
    rotations = []
    translations = []
    rotation_angle = rt_plan_parameters["gantry angle"]
    for n in l_cp:
        rot = Rotation.from_euler("y", rotation_angle[n], degrees=True)
        rot = rot.as_matrix()
        rotations.append(rot)
        translations.append(np.zeros(3))
    plane.add_dynamic_parametrisation(rotation=rotations, translation=translations)


def add_alpha_source(sim, name, nb_part):
    linac = sim.volume_manager.get_volume(name)
    z_linac = linac.size[2]
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    deg = gate.g4_units.deg
    plan_source = sim.add_volume("Box", "plan_alpha_source")
    plan_source.material = "G4_Galactic"
    plan_source.mother = name
    plan_size = np.array([1 * nm, 1 * nm, 1 * nm])
    plan_source.size = np.copy(plan_size)
    plan_source.translation = [0 * mm, 0 * mm, z_linac / 2 - 3.5 * mm]

    source = sim.add_source("GenericSource", "alpha_source")
    Bq = gate.g4_units.Bq
    MeV = gate.g4_units.MeV
    source.particle = "alpha"
    source.attached_to = plan_source.name
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.position.type = "box"
    source.position.size = np.copy(plan_size)
    source.direction.type = "iso"
    source.direction_relative_to_attached_volume = True
    source.direction.momentum = [0, 0, -1]
    source.activity = nb_part * Bq / sim.number_of_threads
    source.direction.theta = [0, 17 * deg]
    source.direction.phi = [0, 360 * deg]


def validation_test_19_rt_plan(
    theoretical_calculation,
    MC_calculation,
    cp_id,
    rt_plan_parameters,
    nb_part_init,
    nb_part_sent,
    tol=0.3,
):
    print(
        "Area from theoretical calculations for the chosen CP:",
        theoretical_calculation,
        "mm2",
    )
    print("Area from MC simulations for the chosen CP:", MC_calculation, "mm2")

    print("Number of particles emitted:", nb_part_sent)
    percentage_diff = (
        100 * (theoretical_calculation - MC_calculation) / theoretical_calculation
    )
    bool_percentage_diff = np.abs(percentage_diff) > tol * 100
    monitor_units = rt_plan_parameters["weight"][cp_id]
    nb_part_theo = nb_part_init * monitor_units
    print("Number of particles theoretically emitted:", int(np.round(nb_part_theo)))
    err_nb_part = np.sqrt(nb_part_theo)
    if (
        (nb_part_sent >= nb_part_theo - 4 * err_nb_part)
        and (nb_part_sent <= nb_part_theo + 4 * err_nb_part)
        and np.sum(bool_percentage_diff) == 0
    ):
        return True
    else:
        print("")
        print("FAIL")
        print(f"mm2 -> {percentage_diff=} (tol={tol}")
        print(f"{np.sum(bool_percentage_diff)=}")
        print(f"{nb_part_sent/nb_part_theo=}")
        print(f"{err_nb_part=}")
        return False


if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test019_linac")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "qt"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.random_seed = 123456789
    # sim.random_seed = "auto"
    sim.check_volumes_overlap = True

    # unit
    nm = gate.g4_units.nm
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.s
    Bq = gate.g4_units.Bq

    # world
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_Galactic"
    a = np.array([0])

    # linac
    versa.add_linac_materials(sim)
    sad = 1000 * mm
    linac = versa.add_empty_linac_box(sim, "linac_box", sad)
    linac.material = "G4_Galactic"

    # jaws

    jaws = versa.add_jaws(sim, linac.name)

    # mlc
    mlc = versa.add_mlc(sim, linac.name)
    mlc_box = sim.volume_manager.get_volume(f"linac_box_mlc")
    mlc_box.material = "G4_Galactic"
    # add alpha source :
    nb_part = 1000000
    z_linac = linac.size[2]
    rt_plan_parameters = rtplan.read(str(paths.data / "DICOM_RT_plan.dcm"))
    MU = 0
    while MU == 0:
        l_cp = [np.random.randint(0, len(rt_plan_parameters["jaws 1"]), 1)[0]]
        # l_cp = [3]
        print("Control point: ", l_cp)
        MU = rt_plan_parameters["weight"][l_cp[0]]
    nb_part = nb_part / MU
    versa.set_linac_head_motion(
        sim, linac.name, jaws, mlc, rt_plan_parameters, sad=sad, cp_id=l_cp
    )

    if sim.visu:
        add_alpha_source(sim, linac.name, 100)
    else:
        add_alpha_source(sim, linac.name, nb_part)

    # Linac head rotation and jaws and mlc translation according to a DICOM rt plan

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1000 * m)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # add water slice with a dose actor and a motion actor
    add_volume_to_irradiate(sim, world.name, l_cp)

    # start simulation
    # The number of particles provided (sim.activity) will be adapted
    # according to the number of MU delivered at each control points.
    versa.set_time_intervals_from_rtplan(sim, rt_plan_parameters, cp_id=l_cp)
    # leaves_position = rt_plan_parameters["leaves"]
    # jaw_1_positions = rt_plan_parameters["jaws 1"]
    # jaw_2_positions = rt_plan_parameters["jaws 2"]

    leaves = rt_plan_parameters["leaves"][l_cp[0]]
    jaws_1 = rt_plan_parameters["jaws 1"][l_cp[0]]
    jaws_2 = rt_plan_parameters["jaws 2"][l_cp[0]]
    jaws = [jaws_1, jaws_2]
    theoretical_area = calc_mlc_aperture(leaves, jaws)

    sim.run()

    # print results
    print(stats)

    # test

    dose2 = sim.get_actor("dose_water_slice")
    img_MC = dose2.edep.image
    # img_MC = itk.imread(dose2.get_output_path("edep"))
    array_MC = itk.GetArrayFromImage(img_MC)
    bool_MC = array_MC[array_MC != 0]
    simulated_area = len(bool_MC) * 1.44
    is_ok = validation_test_19_rt_plan(
        theoretical_area,
        simulated_area,
        l_cp[0],
        rt_plan_parameters,
        nb_part,
        stats.counts.events,
    )
    utility.test_ok(is_ok)
