#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import itk
import uproot
import hist
import opengate as gate

# import xraylib
# import periodictable
from opengate.tests import utility
import os
import glob
import numpy as np

# import matplotlib.pyplot as plt
# import matplotlib.ticker as mticker
from variables import tle_sim
from simu_lecture import simulation
from multijobs2 import (
    DEFAULT_OUTPUT,
    DEFAULT_FILE_NAME,
    DEFAULT_NUMBER_OF_PARTICLES,
    DEFAULT_ACTOR,
)

simu, ct, vpg_actor, source = simulation(
    output=DEFAULT_OUTPUT,
    File_name=DEFAULT_FILE_NAME,
    job_id=0,
    number_of_particles=DEFAULT_NUMBER_OF_PARTICLES,
    visu=False,
    verbose=False,
    actor=DEFAULT_ACTOR,
)

tle_simu = tle_sim(simu, ct, vpg_actor, source)

# FIRST STEP : retrieve the arrays and all the needed features
# CT volume :

ct_object = tle_simu.ct
UH_array = itk.array_from_image(ct_object.load_input_image())

# ACTORS volume as a list of object and the output place:

path = tle_simu.path
actor_object = tle_simu.vpg_actor
feature = ["prot_e", "neutr_e"]
File_name = DEFAULT_FILE_NAME

# database

data_protons = tle_simu.root_file
data_neutrons = tle_simu.root_file_neutron

# SECOND STEP : compute the material Gamma for each materials present in the ct and store it in a list

gamma_neutron = {}
gamma_proton = {}

for x in range(UH_array.shape[2]):
    for y in range(UH_array.shape[1]):
        for z in range(UH_array.shape[0]):
            UH = UH_array[z, y, x]
            if UH not in gamma_neutron:
                gamma_neutron[UH] = tle_simu.gamma_mat(UH, data_neutrons, False)
            if UH not in gamma_proton:
                gamma_proton[UH] = tle_simu.gamma_mat(UH, data_protons, True)


# THIRD STEP : convert the energy histogram stored the 4D output into emission spectra for each voxel of the ct volume

Ep = np.linspace(0, actor_object.energyrange, actor_object.energybins + 1)

output_name = actor_object.name
for type_name in feature:
    file_path = os.path.join(
        path.output, f"{File_name}_{output_name}_1_{type_name}.nii.gz"
    )
    print(file_path)
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"File {file_path} not found in output directory.")
        continue  # Skip to the next iteration if the file does not exist

    # Read the image
    img = itk.imread(file_path)

    if img is None:
        print(f"Image {output_name}_merged_{type_name} not found in output directory.")
    # Convert the image to a numpy array
    array = itk.array_from_image(img)
    treated_array = np.zeros(
        (250, array.shape[1], array.shape[2], array.shape[3])
    )  # Initialize the treated array
    for x in range(array.shape[3]):
        for y in range(array.shape[2]):
            for z in range(array.shape[1]):
                # Get the Hounsfield Unit (HU) value at the current voxel
                X, Y, Z = tle_simu.redim((x, y, z), ct_object, actor_object, array)
                UH = UH_array[X, Y, Z]
                histo_E = array[
                    :, z, y, x
                ]  # Get the energy histogram for the current voxel
                Gamma_m = (
                    gamma_proton[UH]
                    if type_name == "prot_e.nii.gz"
                    else gamma_neutron[UH]
                )
                spectrum = np.zeros(
                    250
                )  # Initialize the spectrum for the current voxel
                for i in range(len(histo_E) - 1):
                    print(histo_E[i])
                    En = (
                        i * actor_object.energyrange / actor_object.energybins
                    )  # Calculate the energy for the current bin
                    bin_index = int(
                        En / (200 / 500)
                    )  # Determine the bin index for the current energy value
                    spectrum = spectrum + Gamma_m[bin_index, :] * histo_E[i]
                treated_array[:, z, y, x] = treated_array[:, z, y, x] + spectrum
# Create a new ITK image from the treated array
itk_output = itk.image_from_array(treated_array)
itk_output.CopyInformation(img)
itk.imwrite(itk_output, path.output / f"VPG_{output_name}_Energy.nii.gz")
