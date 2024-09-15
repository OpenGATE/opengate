#!/usr/bin/env python3

# #################################################################
# This software is distributed under the terms
# of the GNU Lesser General Public Licence (LGPL)
# Hermann Fuchs, Medical University of Vienna / Mayo Clinic Florida
# 10.08.2023
# #################################################################

import opengate as gate
import pathlib
import itk
import numpy as np
import matplotlib.pyplot as plot
from scipy.spatial.transform import Rotation

import opengate.contrib.beamlines.ionbeamline as ionbeamline
import opengate.contrib.tps.ionbeamtherapy as ionbeamtherapy

# from opengate.helpers_rt_plan import *
# from opengate.geometry.helpers_geometry import *
import logging
import argparse
import os
from opengate.tests import utility


# units
km = gate.g4_units.km
m = gate.g4_units.m
mm = gate.g4_units.mm
cm = gate.g4_units.cm
eV = gate.g4_units.eV
MeV = gate.g4_units.MeV
um = gate.g4_units.um
nm = gate.g4_units.nm
km = gate.g4_units.km
gcm3 = gate.g4_units.g / gate.g4_units.cm3
deg = gate.g4_units.deg
mrad = gate.g4_units.mrad


def set_source(sim, n_particles_thread, source_type_str, tp_path):

    ## ---------- DEFINE BEAMLINE MODEL -------------##
    MAbeamline = ionbeamline.BeamlineModel()
    MAbeamline.name = None
    MAbeamline.radiation_types = "ion 6 12"
    # Nozzle entrance to Isocenter distance
    MAbeamline.distance_nozzle_iso = 460.00  # mm
    # SMX to Isocenter distance
    MAbeamline.distance_stearmag_to_isocenter_x = 6700.00
    # SMY to Isocenter distance
    MAbeamline.distance_stearmag_to_isocenter_y = 7420.00
    # polinomial coefficients
    MAbeamline.energy_mean_coeffs = [
        -1.3224984201351649e-08,
        1.7894153922222887e-05,
        -0.008364312581777621,
        13.579959597227932,
        -149.53103267823278,
    ]
    MAbeamline.energy_spread_coeffs = [0.0001]
    MAbeamline.sigma_x_coeffs = [2.0]
    MAbeamline.theta_x_coeffs = [0.0002]
    MAbeamline.epsilon_x_coeffs = [0.0002]
    MAbeamline.sigma_y_coeffs = [2.0]
    MAbeamline.theta_y_coeffs = [0.0002]
    MAbeamline.epsilon_y_coeffs = [0.0002]
    ## --------START PENCIL BEAM SCANNING---------- ##
    # NOTE: HBL means that the beam is coming from -x (90 degree rot around y)
    spots, ntot, energies, G = ionbeamtherapy.spots_info_from_txt(
        tp_path, "ion 6 12", beam_nr=1
    )
    print(dir(spots))
    print(f"{G = }")
    if "tps" in source_type_str.lower():
        # print("sum_weights: ", sum_weights, " sum_beamFraction: ", sum_beamFraction)
        tps = ionbeamtherapy.TreatmentPlanSource("RT_plan", sim)
        tps.set_beamline_model(MAbeamline)
        tps.set_particles_to_simulate(n_particles_thread)
        tps.set_spots(spots)
        tps.rotation = Rotation.from_euler("z", G, degrees=True)
        tps.initialize_tpsource()

        actual_sim_particles = tps.actual_sim_particles

    else:
        set_gps(spots, n_particles_thread, sim, beamline=MAbeamline, gantry_angle=G)


def set_gps(spots, nSim, sim, beamline, gantry_angle):
    for i, spot in enumerate(spots):

        # simulate a fraction of the beam particles for this spot
        nspot = np.round(spot.beamFraction * nSim)

        if nspot == 0:
            continue

        source = sim.add_source("GenericSource", f"gps_spot_{i}")

        # set energy
        source.energy.type = "gauss"
        source.energy.mono = beamline.get_energy(nominal_energy=spot.energy)
        source.energy.sigma_gauss = beamline.get_sigma_energy(
            nominal_energy=spot.energy
        )
        # print(spot.particle_name)
        source.particle = spot.particle_name
        source.position.type = "disc"  # pos = Beam, shape = circle + sigma

        # # set mother
        # if self.mother is not None:
        #     source.mother = self.mother

        # # POSITION:
        # source.position.translation = self._get_pbs_position(spot)

        # # ROTATION:
        # source.position.rotation = self._get_pbs_rotation(spot)
        # source.position.rotation = Rotation.from_euler("z", gantry_angle, degrees=True).as_matrix()
        # source.position.radius = 8 * mm
        source.position.sigma_x = 3 * mm
        source.position.sigma_y = 3 * mm
        source.position.translation = [250 * mm, 0 * mm, 0 * mm]
        source.direction.type = "momentum"
        source.direction.momentum = [-1, 0, 0]

        # add weight
        # source.weight = -1
        source.n = nspot

        # set optics parameters
        # source.direction.partPhSp_x = [
        #     beamline.get_sigma_x(spot.energy),
        #     beamline.get_theta_x(spot.energy),
        #     beamline.get_epsilon_x(spot.energy),
        #     beamline.conv_x,
        # ]
        # source.direction.partPhSp_y = [
        #     beamline.get_sigma_y(spot.energy),
        #     beamline.get_theta_y(spot.energy),
        #     beamline.get_epsilon_y(spot.energy),
        #     beamline.conv_y,
        # ]


def simulation(
    data_path,
    output_path,
    number_of_particles=1,
    tp_path="",
    source_type_str="tps",
    calc_LETd=False,
):
    """Run Gate simulation"""
    number_of_threads_for_simulation = os.cpu_count()
    n_particles_thread = number_of_particles / number_of_threads_for_simulation

    # simulation object
    sim = gate.Simulation()
    ui = sim.user_info
    # print(ui)

    ui.running_verbose_level = 0
    # ui.running_verbose_level = 0

    ui.g4_verbose = False
    ui.g4_verbose_level = 0

    # Visualization
    ui.visu = False
    # ui.visu_type = "vrml"
    ui.visu_verbose = False

    ui.random_engine = "MersenneTwister"
    ui.random_seed = "auto"
    # self.random_seed = 123456789
    ui.number_of_threads = number_of_threads_for_simulation

    # Materials
    sim.volume_manager.add_material_database(data_path / "GateMaterials.db")

    # ######################################################################
    # # Defining geometry world plus patient
    # ######################################################################
    # geometry
    # There is a default volume called world (lowercase)
    #  change world size
    world = sim.world
    world.size = [11 * m, 5 * m, 5 * m]
    world.material = "Air"

    # adding nozzle
    # nozzle.create_gantry_nozzle(sim)
    # nozzle.create_FX_nozzle(sim, nozzle_position=100)
    print("Volume tree:")
    print(sim.volume_manager.dump_volume_tree())

    patient = sim.add_volume("Box", "patient")
    print(patient)  # to display the default parameter values
    patient.material = "G4_WATER"
    patient.mother = "world"  # by default
    patient.size = [500 * mm, 400 * mm, 400 * mm]
    # # rotation of the patient
    rotation_matrix = Rotation.from_euler("z", 180, degrees=True).as_matrix()
    patient.rotation = rotation_matrix

    # ######################################################################
    # # Defining actors
    # ######################################################################
    base_name = f"SOBP_{source_type_str}_{number_of_particles:.0f}"
    # Statistics Actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    new_joined_path = os.path.join(output_path, base_name + "Statistics" + ".txt")
    stats.output = new_joined_path
    stats.track_types_flag = True

    # calculate actor size and spacing based on patient size and resolution
    target_voxel_size = [1.0 * mm, patient.size[1] * mm, patient.size[2] * mm]
    # target_voxel_size = [1 * mm, 1 * mm, 1 * mm]

    is_dimensions = [
        int(patient.size[0] / target_voxel_size[0]),
        int(patient.size[1] / target_voxel_size[1]),
        int(patient.size[2] / target_voxel_size[2]),
    ]
    # print("is_dimensions", is_dimensions)
    # print("is_voxel_size", is_voxel_size)

    # ###############################
    # # Dose Actor
    dose = sim.add_actor("DoseActor", "dose")
    # dose.output_filename = output_path / "OneDimDose.mhd"
    dose.attached_to = "patient"
    # dose.spacing = is_voxel_size
    dose.spacing = target_voxel_size
    # print("dose.spacing", dose.spacing)
    dose.size = is_dimensions

    # # number of voxels per dimension
    # dose.size = [517, 460, 228]
    # # size of the voxels
    # dose.spacing = [0.9765625 * mm, 0.9765625 * mm, 2 * mm]
    dose.uncertainty = False
    dose.use_more_ram = False
    dose.hit_type = "random"

    dose.dose = False
    new_joined_path = os.path.join(output_path, base_name + "Dose" + ".mhd")
    dose.output_filename = new_joined_path

    if calc_LETd:
        # # LET Actor
        letactor = sim.add_actor("LETActor", "let")
        # letactor.output = output_path / "OneDimletactor.mhd"
        letactor.mother = "patient"
        # letactor.spacing = is_voxel_size
        letactor.spacing = target_voxel_size
        # print("letactor.spacing", letactor.spacing)
        letactor.size = is_dimensions
        letactor.dose_average = True
        new_joined_path = os.path.join(output_path, base_name + "LET" + ".mhd")
        letactor.output = new_joined_path
        dir(letactor)

    # ######################################################################
    # # Defining pencil beam source
    # ######################################################################

    set_source(sim, n_particles_thread, source_type_str, tp_path)

    # ######################################################################
    # # Defining physics
    # ######################################################################

    # sim.physics_manager.physics_list_name = "FTFP_BERT"
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    global_cut = 100 * cm
    sim.physics_manager.global_production_cuts.gamma = global_cut
    sim.physics_manager.global_production_cuts.electron = global_cut
    sim.physics_manager.global_production_cuts.positron = global_cut
    sim.physics_manager.global_production_cuts.proton = global_cut

    # # adding cuts for waterphantom
    # reg = sim.physics_manager.add_region("reg")
    # reg.max_step_size = 0.1 * mm
    # reg.production_cuts.gamma = 0.1 * mm
    # reg.production_cuts.electron = 0.1 * mm
    # reg.production_cuts.positron = 0.1 * mm
    # reg.production_cuts.proton = 0.1 * mm
    # # reg.associate_volume("waterbox")
    # reg.associate_volume("patient")

    # sim.physics_manager.set_user_limits_particles("all")

    # # sim.initialize()
    # print("Phys list cuts to be used: ", sim.physics_manager.dump_production_cuts())
    # # print("info physics lists ", sim.physics_manager.dump_info_physics_lists())
    # print(sim.physics_manager)
    # print("Volume tree:")
    # print(sim.volume_manager.dump_volume_tree())

    # print("Number of sources: ", sim.dump_sources())

    # # start simulation
    # # ~ output = sim.start()
    output = sim.run(start_new_process=True)
    dose_fpath = sim.get_actor("dose").user_info.output
    if calc_LETd:
        let_fpath = sim.get_actor("let").user_info.output
    else:
        let_fpath = ""
    return output, dose_fpath, let_fpath


def eval_data(dose_ref_fpath, dose_fpath, scale_img2=1.0):
    utility.assert_images(
        dose_ref_fpath,
        dose_fpath,
        axis="x",
        scaleImageValuesFactor=scale_img2,
    )


def main():
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    print("Running Gate Simulation")
    current_path = pathlib.Path(__file__).parent.resolve()
    data_path = current_path / "../data"
    output_path = current_path / "../temp"
    # number_of_particles = 100000
    number_of_particles_1 = 1e4
    source_type_str = "gps"
    calc_LETd = False
    tp_path = data_path / "tpsource/SOBP_HFU_23_02_2024.txt"
    simLink, dose_1e5_fpath, let_fpath_1e5 = simulation(
        data_path,
        output_path,
        number_of_particles=number_of_particles_1,
        tp_path=tp_path,
        source_type_str=source_type_str,
        calc_LETd=calc_LETd,
    )
    number_of_particles_2 = 1.0e5

    simLink, dose_fpath, let_fpath = simulation(
        data_path,
        output_path,
        number_of_particles=number_of_particles_2,
        tp_path=tp_path,
        source_type_str=source_type_str,
        calc_LETd=calc_LETd,
    )
    scale_img2 = number_of_particles_1 / number_of_particles_2
    eval_data(dose_1e5_fpath, dose_fpath, scale_img2=scale_img2)
    if calc_LETd:
        eval_data(let_fpath_1e5, let_fpath)
    print("Simulation finished")


if __name__ == "__main__":
    main()
