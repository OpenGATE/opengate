#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.linacs.elektaversa as versa
import opengate.contrib.linacs.dicomrtplan as rtplan
from opengate.tests import utility
from opengate.utility import g4_units
import numpy as np
import uproot


def add_volume_to_irradiate(sim, name):
    m = g4_units.m
    patient = sim.add_volume("Box", "water_plane")
    patient.mother = name
    patient.material = "G4_Galactic"
    patient.size = [1 * m, 0.5 * m, 0.25 * m]
    patient.color = [1, 0, 0, 1]  # red
    return patient


def add_phase_space_isocenter(sim, name, pos):
    isocenter_sphere = sim.add_volume("Sphere", "sphere")
    isocenter_sphere.material = "G4_Galactic"
    isocenter_sphere.mother = name
    isocenter_sphere.translation = pos
    isocenter_sphere.radius = 1 * cm
    isocenter_sphere.color = [0, 1, 0, 1]  # red

    phsp = sim.add_actor("PhaseSpaceActor", f"phsp")
    phsp.attached_to = isocenter_sphere.name
    phsp.attributes = ["EventID"]
    return phsp


def add_alpha_source(sim, name, pos_Z, nb_part):
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    plan_source = sim.add_volume("Box", "plan_alpha_source")
    plan_source.material = "G4_Galactic"
    plan_source.mother = name
    plan_size = np.array([1 * nm, 1 * nm, 1 * nm])
    plan_source.size = np.copy(plan_size)
    plan_source.translation = [0 * mm, 0 * mm, -pos_Z / 2 + 300 * mm]

    source = sim.add_source("GenericSource", "alpha_source")
    MeV = gate.g4_units.MeV
    source.particle = "alpha"
    source.mother = plan_source.name
    source.energy.type = "mono"
    source.energy.mono = 1 * MeV
    source.position.type = "box"
    source.position.size = np.copy(plan_size)
    source.direction.type = "momentum"
    source.direction_relative_to_attached_volume = True
    source.direction.momentum = [0, 0, -1]
    source.n = nb_part


def validation_test_19_rt_plan(array, nb_part):
    if len(array["EventID"]) == nb_part:
        return True
    else:
        return False


if __name__ == "__main__":
    # paths
    paths = utility.get_default_test_paths(__file__, output_folder="test019_linac")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    sim.number_of_threads = 1
    sim.output_dir = paths.output  # FIXME (not yet)
    sim.random_seed = 123456789
    sim.check_volumes_overlap = True
    sim.output_dir = paths.output

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

    # materials and empty linac
    versa.add_linac_materials(sim)
    sad = 1000 * mm
    linac = versa.add_empty_linac_box(sim, "linac_box", sad)
    linac.material = "G4_Galactic"

    # add alpha source :
    nb_part = np.random.randint(1, 100)
    z_linac = linac.size[2]
    add_alpha_source(sim, linac.name, z_linac / 2 - 5.6 * mm, nb_part)

    # Linac head rotation and jaws and mlc translation according to a DICOM rt plan
    cp = np.random.randint(1, 230, 1)[0]
    print(cp)
    rt_plan_parameters = rtplan.read(str(paths.data / "DICOM_RT_plan.dcm"))
    versa.rotation_around_user_point(
        sim, linac.name, "x", rt_plan_parameters["gantry angle"][cp]
    )

    # The patient image is simulated at a position which is the center of the simulation
    # regardless the offset of the image
    # And the isocenter is given the real center of the image. That's why we have
    # to correct the isocenter of the real image center
    center_patient_on_DICOM_img = np.array([11 * mm, -194 * mm, 45 * mm])
    vector_translation_isocenter_to_center = (
        center_patient_on_DICOM_img - rt_plan_parameters["isocenter"][cp]
    )
    print(vector_translation_isocenter_to_center)

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1000 * m)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # add water slice with a dose actor and a motion actor
    volume = add_volume_to_irradiate(sim, world.name)
    phsp = add_phase_space_isocenter(
        sim, volume.name, vector_translation_isocenter_to_center
    )
    phsp.output_filename = "phsp_versa_mlc_RT_plan.root"
    print(phsp.get_output_path())

    translation_volume = volume.translation
    new_translation = (
        np.array(translation_volume) - vector_translation_isocenter_to_center
    )
    volume.translation = new_translation

    # start simulation
    # The number of particles provided (sim.activity) will be adapted regarding
    # the number of MU delivered at each control points.
    sim.run()

    # print results
    print(stats)

    f_phsp = uproot.open(phsp.get_output_path())
    arr = f_phsp["phsp"].arrays()

    # test
    is_ok = validation_test_19_rt_plan(arr, nb_part)
    utility.test_ok(is_ok)
