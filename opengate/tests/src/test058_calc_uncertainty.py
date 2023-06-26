#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import pathlib
from scipy.spatial.transform import Rotation
import gatetools.phsp as phsp
import matplotlib.pyplot as plt
import numpy as np
import itk


def assert_uncertainty(
    img_E, img_err_E, nb_part, mean_E, std_E, tolerance=0.075, is_ok=True
):
    val_E_img = img_E[0, 0, 0]
    val_err_E_img = round(val_E_img * img_err_E[0, 0, 0], 3)
    val_E_img = round(val_E_img, 2)

    print(
        "Energy deposited in the voxel for "
        + str(round(nb_part))
        + " particles : "
        + str(val_E_img)
        + " MeV"
    )
    print("Theoretical deposited energy : " + str(mean_E * nb_part) + " MeV")
    print(
        "Standard error on the deposited energy in the voxel for "
        + str(round(nb_part))
        + " particles : "
        + str(val_err_E_img)
        + " MeV"
    )
    print(
        "Theoretical standard error on deposited energy : "
        + str(round(std_E * np.sqrt(nb_part), 3))
        + " MeV"
    )
    print("Tolerance : " + str(100 * tolerance) + " %")

    var_E = abs((val_E_img - (mean_E * nb_part))) / (mean_E * nb_part)
    var_err_E = abs((val_err_E_img - (std_E * np.sqrt(nb_part)))) / (
        std_E * np.sqrt(nb_part)
    )

    if var_E > tolerance or var_err_E > tolerance:
        is_ok = False

    return is_ok


current_path = pathlib.Path(__file__).parent.resolve()
output_path = current_path / ".." / "output"

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
# ui.visu_type = "vrml"
ui.check_volumes_overlap = False
# ui.running_verbose_level = gate.EVENT
ui.number_of_threads = 1
ui.random_seed = "auto"

# units
m = gate.g4_units("m")
km = gate.g4_units("km")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
MeV = gate.g4_units("MeV")
keV = gate.g4_units("keV")
gcm3 = gate.g4_units("g/cm3")

#  adapt world size
world = sim.world
world.size = [200 * m, 200 * m, 201 * m]

block_size = [200 * m, 200 * m, 200 * m]


# Tungsten block


gate.new_material_weights("Tungsten", 19.3 * gcm3, "W")
t_block = sim.add_volume("Box", "T_block")
t_block.mother = world.nameoutput_path = current_path / ".." / "output"
t_block.material = "Tungsten"
t_block.size = block_size
t_block.translation = [0 * mm, 0 * mm, -0.5 * m]
t_block.color = [0, 1, 0, 1]
t_block.mother = world.name


# source

nb_part = 1000 / ui.number_of_threads
std_dev_E = 10 * keV
mean_E = 100 * keV
source = sim.add_source("GenericSource", "photon_source")
source.particle = "gamma"
source.n = nb_part
source.position.type = "box"
source.position.size = [3 * cm, 3 * cm, 0 * cm]
source.direction.type = "momentum"
source.mother = world.name
source.direction.momentum = [0, 0, -1]
source.energy.type = "gauss"
source.energy.mono = mean_E
source.energy.sigma_gauss = std_dev_E


s = sim.add_actor("SimulationStatisticsActor", "Stats")
# s.track_types_flag = True

# add dose actor
dose = sim.add_actor("DoseActor", "dose")
dose.output = output_path / "test057-uncertainty.mhd"
dose.mother = t_block.name
dose.size = [1, 1, 1]
dose.spacing = block_size
dose.img_coord_system = True
dose.uncertainty = True
dose.translation = [0 * mm, 0 * mm, -0.5 * m]
dose.hit_type = "random"

# Physic list and cuts
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option3"
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 1 * km
cuts.world.electron = 1 * km
cuts.world.positron = 1 * km


output = sim.start()

# print results
stats = output.get_actor("Stats")
print(stats)

# Open images for comparison

img_E = itk.imread(output_path / "test057-uncertainty.mhd")
array_E = itk.GetArrayFromImage(img_E)
err_img_E = itk.imread(output_path / "test057-uncertainty_uncertainty.mhd")
err_array_E = itk.GetArrayFromImage(err_img_E)


is_ok = assert_uncertainty(array_E, err_array_E, nb_part, mean_E, std_dev_E)
gate.test_ok(is_ok)
