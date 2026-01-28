#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.utility import g4_units
from opengate.contrib.linacs import elektaversa as versa
from opengate.contrib.linacs import dicomrtplan as rtplan
from scipy.spatial.transform import Rotation
import numpy as np
import itk


def information_img_patient(path_img=None, open_img=True, img=None):
    if open_img:
        image = itk.imread(path_img)
        offset = np.array(image.GetOrigin())
        dim = np.array(image.GetLargestPossibleRegion().GetSize())
        spacing = np.array(image.GetSpacing())
    else:
        offset = np.array(img.GetOrigin())
        dim = np.array(img.GetLargestPossibleRegion().GetSize())
        spacing = np.array(img.GetSpacing())

    return (offset, dim, spacing)


def add_dose_actor_on_patient_image(
    sim, patient, dim, spacing, do_tle, tle_type, tle_threshold
):
    MeV = gate.g4_units.MeV
    mm = gate.g4_units.mm
    if do_tle == True:
        tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
        tle_dose_actor.attached_to = patient.name
        tle_dose_actor.dose_uncertainty.active = True
        tle_dose_actor.edep_uncertainty.active = False
        tle_dose_actor.density.active = False
        tle_dose_actor.hit_type = "random"
        tle_dose_actor.dose.active = True
        tle_dose_actor.dose_squared.active = True
        tle_dose_actor.edep.active = True
        tle_dose_actor.edep.write_to_disk = False
        tle_dose_actor.size = np.array(np.round(dim), dtype=int)
        tle_dose_actor.spacing = np.array(spacing, dtype=float)
        tle_dose_actor.output_coordinate_system = "attached_to_image"
        # the following option is important: if TLE is used for gammas with too high energy, the
        # resulting dose will be biased. The energy threshold depends on the voxels size of the
        # dose actor. Here the bias is clearly visible if TLE is used above 1.2 MeV.
        # With the threshold enabled, no acceleration for high enery gamma, but no bias.
        tle_dose_actor.tle_threshold_type = tle_type
        tle_dose_actor.tle_threshold = tle_threshold * mm
        print(tle_dose_actor.tle_threshold)
        tle_dose_actor.database = "EPDL"

    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = patient.name
    dose.size = np.array(np.round(dim), dtype=int)
    dose.spacing = np.array(spacing, dtype=float)
    dose.output_coordinate_system = "attached_to_image"
    dose.dose_uncertainty.active = True
    dose.dose_squared.active = True
    dose.density.active = False
    dose.translation = [0, 0, 0]
    dose.hit_type = "random"
    dose.dose.active = True
    dose.edep.write_to_disk = False


def add_patient_image(
    sim,
    name,
    path_image,
    img,
    cp_param,
    do_tle=False,
    tle_type="energy",
    tle_threshold=1.6,
    RPL=False,
):
    # OPEN IMAGE AND ASSOCIATION OF DENSITY TO EACH VOXELS
    gcm3 = gate.g4_units.g / gate.g4_units.cm3
    offset, dim, spacing = information_img_patient(path_image + img)
    translation, rotation = (
        versa.get_patient_translation_and_rotation_from_RT_plan_to_IEC(
            cp_param, path_image + img
        )
    )
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="advanced_test_linac"
    )

    ### ADD PATIENT
    patient = sim.add_volume("Image", "patient")
    patient.image = path_image + img
    patient.mother = name
    patient.material = "G4_AIR"  # material used by default
    f1 = paths.data / "Schneider2000MaterialsTable.txt"
    f2 = paths.data / "Schneider2000DensitiesTable.txt"
    tol = 0.05 * gcm3
    patient.voxel_materials, materials = (
        gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    )
    patient.color = [1, 0, 1, 1]
    patient.rotation = rotation
    patient.translation = translation

    # #ADD DOSE ACTOR
    add_dose_actor_on_patient_image(
        sim, patient, dim, spacing, do_tle, tle_type, tle_threshold
    )
    return patient


def add_phase_space_actor(sim, mother_name, ssd):

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    volume_list = sim.volume_manager.volumes.keys()
    mother = sim.volume_manager.get_volume(mother_name)
    if not "phase_space_plan" in volume_list:
        phsp_plan = sim.add_volume("Box", "phase_space_plan")
        phsp_plan.size = [mother.size[0], mother.size[1], 1 * nm]
        phsp_plan.mother = mother_name
        mother_volume = sim.volume_manager.get_volume(mother_name)

        z_pos = 100 * cm - ssd - phsp_plan.size[2] / 2
        phsp_plan.translation = [0, 0, z_pos]
    else:
        phsp_plan = sim.volume_manager.get_volume("phase_space_plan")
    phsp_plan.color = [0.7, 0.3, 0.3, 0.8]

    phsp = sim.add_actor("PhaseSpaceActor", "phase_space_actor")
    phsp.attached_to = phsp_plan.name
    phsp.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
        "TrackID",
    ]
    return phsp_plan


def init_simulation(
    dcm_RP,
    arc_id,
    path_img,
    img,
    mode=0,
    vis=False,
    tle_type=0,
    tle_threshold=1.6,
    shielding=True,
    lead_thickness=4,
):
    tle_types = ["energy", "max range", "average range"]
    l_mode = ["Normal", "TLE"]
    mode = l_mode[mode]
    tle_type = tle_types[tle_type]
    sim = gate.Simulation()
    ui = sim.user_info
    ui.running_verbose_level = gate.logger.RUN
    # main options
    sim.g4_verbose = False

    sim.visu = vis
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.check_volumes_overlap = True
    cp_id = "all_cp"

    # unit
    nm = gate.g4_units.nm
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq

    # world
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # linac
    sad = 1000 * mm
    linac = versa.add_linac(sim, "linac_box", sad)
    linac.material = "G4_AIR"
    linac.color = [0.78, 0.129, 0.92, 0.3]

    small_linac_box = versa.add_patient_dependent_linac_box(sim, linac.name)
    mlc_leaves = versa.add_mlc(sim, linac.name, small_linac_box.name)
    mlc = sim.volume_manager.get_volume(f"{small_linac_box.name}_mlc")
    jaws = versa.add_jaws(sim, linac.name, small_linac_box.name)

    if shielding:
        versa.add_linac_shielding(
            sim,
            linac.name,
            small_linac_box.name,
            type="all",
            lead_thickness=lead_thickness,
        )

    rt_plan_parameters = rtplan.read(dcm_RP, arc_id=arc_id)
    cp_list = [None]
    if cp_list[0] != None:
        l_cp = cp_list
        new_rt_plan_parameters = {}
        for key in rt_plan_parameters.keys():
            value = rt_plan_parameters[key][l_cp]
            new_rt_plan_parameters[key] = value
        rt_plan_parameters = new_rt_plan_parameters

    else:
        l_cp = np.arange(0, len(rt_plan_parameters["jaws 1"]), 1)

    versa.set_time_intervals_from_rtplan(sim, rt_plan_parameters)

    versa.set_linac_head_motion(
        sim, linac.name, jaws, mlc_leaves, rt_plan_parameters, sad=sad
    )

    plan = sim.add_volume("Box", "plan")
    plan.material = "G4_AIR"
    plan.mother = linac.name
    plan.size = [linac.size[0], linac.size[1], 0.1 * nm]
    plan.translation = [0, 0, linac.size[2] / 2 - 30.01 * cm + 0.5 * nm]
    source = versa.add_phase_space_source(sim, plan.name)
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    source.weight_key = "Weight"
    source.PDGCode_key = "PDGCode"

    if mode == "Normal":
        add_patient_image(
            sim, world.name, path_img, img, rt_plan_parameters, do_tle=False
        )
    if mode == "TLE":
        print("lol")
        add_patient_image(
            sim,
            world.name,
            path_img,
            img,
            rt_plan_parameters,
            do_tle=True,
            tle_type=tle_type,
            tle_threshold=tle_threshold,
        )

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "electron", 1000 * m)
    volume_list = sim.volume_manager.volumes.keys()
    if "patient" in volume_list:
        sim.physics_manager.set_production_cut("patient", "electron", 0.05 * mm)
    # add stat actor
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)
    if mode == "TLE":
        s = f"/process/eLoss/CSDARange true"
        sim.g4_commands_before_init.append(s)
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # print results
    return sim, rt_plan_parameters
