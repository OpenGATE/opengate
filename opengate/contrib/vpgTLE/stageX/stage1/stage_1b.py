#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import itk
from opengate.tests import utility
import os
import glob
import numpy as np
from variables import tle_sim
from stage_1a import *

# from multijobs_stage_1a import *

sim = simulation(
    output=output,
    File_name=File_name,
    job_id=0,
    number_of_particles=number_of_particles,
    visu=False,
    verbose=False,
    actor=actor,
    Erange=Erange,
)


tle_simu = tle_sim(sim)

# FIRST STEP : retrieve the arrays and all the needed features
# CT volume :

ct_object = tle_simu.ct
UH_array = itk.array_from_image(ct_object.load_input_image())

# ACTORS volume as a list of object and the output place:
path = tle_simu.path
actor = tle_simu.act
actor_list = tle_simu.actor_list

# database

data_protons = tle_simu.root_file
data_neutrons = tle_simu.root_file_neutron
mat = tle_simu.voxel_mat

# SECOND STEP : compute the material Gamma for each materials present in the ct and store it in a list

gamma_neutron = {}
gamma_proton = {}

for data in mat:
    name = data[2]
    gamma_neutron[name] = tle_simu.gamma_mat(name, data_neutrons)
    gamma_proton[name] = tle_simu.gamma_mat(name, data_protons)

# THIRD STEP : convert the energy histogram stored the 4D output into emission spectra for each voxel of the ct volume

for act in actor_list:
    Ep = np.linspace(0, actor.energyrange, actor.energybins + 1)
    file_pat = os.path.join(path.output / f"{File_name}_*.nii.gz")
    file_list = sorted(glob.glob(file_pat))
    for type_name in actor_list:
        img = itk.imread(os.path.join(path.output, f"{File_name}_{type_name}"))
        if img is None:
            print(f"Image {File_name}_{type_name} not found in output directory.")
        # Convert the image to a numpy array
        array = itk.array_from_image(img)
        treated_array = np.zeros(
            (250, array.shape[1], array.shape[2], array.shape[3])
        )  # Initialize the treated array
        gamma_array = np.zeros((250, array.shape[1], array.shape[2], array.shape[3]))
        for x in range(array.shape[3]):
            for y in range(array.shape[2]):
                for z in range(array.shape[1]):
                    # Get the Hounsfield Unit (HU) value at the current voxel
                    if ct_object.size == actor.size:
                        # If the CT size matches the actor size, use the voxel coordinates directly
                        X, Y, Z = x, y, z
                    else:
                        X, Y, Z = tle_simu.redim((x, y, z), ct_object, actor, array)
                    if UH_array[Z, Y, X] == -3024:
                        # Skip the voxel if HU value is -3024
                        continue
                    name = tle_simu.voxel_to_mat_name(
                        UH_array[Z, Y, X], tle_simu.voxel_mat
                    )
                    histo_E = array[
                        :, z, y, x
                    ]  # Get the energy histogram for the current voxel
                    Gamma_m = (
                        gamma_proton[name]
                        if type_name == "prot_e.nii.gz"
                        else gamma_neutron[name]
                    )
                    spectrum = np.zeros(
                        250
                    )  # Initialize the spectrum for the current voxel
                    for i in range(len(histo_E) - 1):  # avoiding the overflow bin
                        En = (
                            i * actor.energyrange / actor.energybins
                        )  # Calculate the energy for the current bin
                        bin_index = int(
                            En / (200 / 500)
                        )  # Determine the bin index for the current energy value
                        spectrum = spectrum + Gamma_m[bin_index, :] * histo_E[i]
                    treated_array[:, z, y, x] = spectrum
        # Create a new ITK image from the treated array
        gamma_array += treated_array
        itk_output = itk.image_from_array(treated_array)
        itk_output.CopyInformation(img)
        itk.imwrite(itk_output, path.output / f"VPG_{File_name}_{type_name}")
    itk_output = itk.image_from_array(gamma_array)
    itk_output.CopyInformation(img)
    itk.imwrite(itk_output, path.output / f"VPG_{File_name}_gamma_e.nii.gz")
