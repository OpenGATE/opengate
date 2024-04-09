#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import numpy as np
import itk
import test069_rotation_DICOM_RT_plan_helpers as helpers
import test069_rotation_DICOM_RT_plan_dynamic_helpers as t
from opengate.tests import utility


def add_VolumeToIrradiate(sim, name, rot_volume):
    mm = gate.g4_units.mm
    # FIXME: Why does this box volume have the name 'cylinder'?
    Box = sim.add_volume("Box", "cylinder")
    Box.material = "G4_WATER"
    Box.mother = name
    Box.size = [400 * mm, 400 * mm, 400 * mm]

    voxel_size_x = 0.5 * mm
    voxel_size_y = 0.5 * mm
    voxel_size_z = 400 * mm

    dim_box = [
        400 * mm / voxel_size_x,
        400 * mm / voxel_size_y,
        400 * mm / voxel_size_z,
    ]
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = "output/testilol.mhd"
    dose.mother = Box.name
    dose.size = [int(dim_box[0]), int(dim_box[1]), int(dim_box[2])]
    dose.spacing = [voxel_size_x, voxel_size_y, voxel_size_z]
    dose.uncertainty = False
    dose.square = False
    dose.hit_type = "random"

    Box.add_dynamic_parametrisation(rotation=rot_volume)

    # motion_tubs = sim.add_actor("MotionVolumeActor", "Move_Tubs")
    # motion_tubs.mother = Box.name
    # motion_tubs.rotations = []
    # motion_tubs.translations = []
    # for i in range(len(rot_volume)):
    #     motion_tubs.rotations.append(rot_volume[i])
    #     motion_tubs.translations.append([0, 0, 0])


def launch_simulation(
    nt, path_img, img, file, output_path, output, nb_part, src_f, vis, seg_cp, patient
):
    visu = vis
    km = gate.g4_units.km
    nb_cp = t.liste_CP(file)
    nb_aleatoire = np.random.randint(0, nb_cp - 1, 4)
    print("Control Points ID: ", nb_aleatoire)
    seg_cp += 1
    l_aperture_voxel = np.zeros(len(nb_aleatoire))
    l_aperture_calc = np.zeros(len(nb_aleatoire))
    for i in range(len(nb_aleatoire)):
        cp_param = t.Dataset_DICOM_MLC_jaws(
            file, [nb_aleatoire[i], nb_aleatoire[i] + 1], 0
        )
        mean_leaves = (cp_param["Leaves"][0] + cp_param["Leaves"][1]) / 2
        mean_jaws_1 = (cp_param["Y_jaws_1"][0] + cp_param["Y_jaws_1"][1]) / 2
        mean_jaws_2 = (cp_param["Y_jaws_2"][0] + cp_param["Y_jaws_2"][1]) / 2
        y_jaws = [mean_jaws_1, mean_jaws_2]
        area = helpers.calc_mlc_aperture(mean_leaves, y_jaws)
        l_aperture_calc[i] = area
        sim = t.init_simulation(
            nt,
            cp_param,
            path_img,
            img,
            visu,
            src_f,
            bool_phsp=False,
            seg_cp=seg_cp,
            patient=patient,
        )

        ui = sim.user_info
        ui.running_verbose_level = gate.logger.RUN

        linac = sim.volume_manager.volumes["Linac_box"]
        world = sim.volume_manager.volumes["world"]
        linac.material = "G4_Galactic"
        world.material = "G4_Galactic"
        # motion_actor = sim.get_actor_user_info("Move_LINAC")
        # rotation_volume = motion_actor.rotations
        # We called this dynamic parametrisation 'rotation_linac'
        rotation_volume = linac.dynamic_params["rotation_linac"]["rotation"]
        helpers.add_alpha_source(sim, linac.name, linac.size[2], nb_part)
        add_VolumeToIrradiate(sim, world.name, rotation_volume)

        dose_actor = sim.get_actor_user_info("dose")
        dose_actor.output = output_path / output

        ui.visu = visu
        if visu:
            ui.visu_type = "vrml"
        sim.physics_manager.global_production_cuts.gamma = 1 * km
        sim.physics_manager.global_production_cuts.electron = 1 * km
        sim.physics_manager.global_production_cuts.positron = 1 * km
        sec = gate.g4_units.s
        sim.run_timing_intervals = []
        for j in range(len(rotation_volume)):
            sim.run_timing_intervals.append([j * sec, (j + 1) * sec])

        sim.run(start_new_process=True)
        img_MC = itk.imread(output_path / "img_test_069-edep.mhd")
        array_MC = itk.GetArrayFromImage(img_MC)
        bool_MC = array_MC[array_MC != 0]
        l_aperture_voxel[i] = len(bool_MC) / 4
    is_ok = helpers.validation_test(l_aperture_calc, l_aperture_voxel)
    utility.test_ok(is_ok)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__)
    output_path = paths.output
    patient = False
    nt = 1
    ###### The three following variables are here to not modify the main program (the helpers) which need it ######
    path_img = "useless"
    img = "useless"
    src_f = "alpha"
    ###############################################################################################################
    output = "img_test_069.mhd"
    nb_part = 750000
    seg_cp = 1
    vis = False
    file = str(paths.data / "DICOM_RT_plan.dcm")
    launch_simulation(
        nt,
        path_img,
        img,
        file,
        output_path,
        output,
        nb_part,
        src_f,
        vis,
        seg_cp,
        patient,
    )
