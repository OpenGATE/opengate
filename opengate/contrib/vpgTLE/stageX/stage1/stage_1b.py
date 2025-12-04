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
from stage_1a import *

# from multijobs_stage1 import output, File_name, number_of_particles, actor, Erange

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

neutr = False  # to skip step if neutron are not taling into account
if "neutr_e.nii.gz" in actor_list:
    neutr = True

gamma_neutron = {}
gamma_proton = {}

# building a dico that links for each mterial name, the Gamma histograms
for data in mat:
    name = data[2]
    if neutr:
        gamma_neutron[name] = tle_simu.gamma_mat(name, data_neutrons)
    gamma_proton[name] = tle_simu.gamma_mat(name, data_protons)

# THIRD STEP : convert the energy histogram stored the 4D output into emission spectra for each voxel of the ct volume
Ep = np.linspace(0, actor.energyrange, actor.energybins + 1)
E_db = np.linspace(0, 200, 500)
ind_db = np.abs(E_db[None, :] - Ep[:, None]).argmin(
    axis=1
)  # LOOKHERE :: should find a better way to build the index list

if MJ:  # multijobs or not ??
    img_p = itk.imread(os.path.join(path.output, f"{File_name}_merged_prot_e.nii.gz"))
else:
    img_p = itk.imread(os.path.join(path.output, f"{File_name}_0_prot_e.nii.gz"))

array_p = itk.array_from_image(img_p)
treated_array_p = np.zeros(
    (250, array_p.shape[1], array_p.shape[2], array_p.shape[3])
)  # Initialize the treated array for proton

treated_array_n = np.zeros(
    (250, array_p.shape[1], array_p.shape[2], array_p.shape[3])
)  # Initialize the treated array for neutron
gamma_array = np.zeros(
    (250, array_p.shape[1], array_p.shape[2], array_p.shape[3])
)  # Initialize the treated array for neutron AND proton

if neutr:
    if MJ:
        img_n = itk.imread(
            os.path.join(path.output, f"{File_name}_merged_neutr_e.nii.gz")
        )
    else:
        img_n = itk.imread(os.path.join(path.output, f"{File_name}_0_neutr_e.nii.gz"))
    array_n = itk.array_from_image(img_n)

# treatment of the image voxel by voxel => to store gamma emission spectrum in each voxel
for x in range(array_p.shape[3]):
    for y in range(array_p.shape[2]):
        for z in range(array_p.shape[1]):
            # Get the Hounsfield Unit (HU) value at the current voxel
            if ct_object.size == actor.size:
                # If the CT size matches the actor size, use the voxel coordinates directly
                X, Y, Z = x, y, z
            else:
                X, Y, Z = tle_simu.redim((x, y, z), ct_object, actor, array_p)
            if (
                UH_array[Z, Y, X] == -3024
            ):  # LOOKHERE : conditions of the CT where there is no matter, to be removed if CT different from the exemple case
                # Skip the voxel if HU value is -3024
                continue
            name = tle_simu.voxel_to_mat_name(UH_array[Z, Y, X], tle_simu.voxel_mat)
            histo_E_p = array_p[
                :, z, y, x
            ]  # Get the energy histogram for the current voxel
            spectrum_p = np.zeros(250)  # Initialize the spectrum for the current voxel
            if histo_E_p.sum() != 0:  # if nothing is detected, the voxel is not treated
                Gamma_m_p = gamma_proton[name]
                Gamma_p = Gamma_m_p[ind_db]
                spectrum_p = np.dot(
                    histo_E_p, Gamma_p
                )  # np.dot : method used for the spectrum computation BUT, can be optimised ???
                treated_array_p[:, z, y, x] = spectrum_p
            if neutr:
                histo_E_n = array_n[:, z, y, x]
                spectrum_n = np.zeros(250)
                if histo_E_n.sum() != 0:
                    Gamma_m_n = gamma_neutron[name]
                    Gamma_n = Gamma_m_n[ind_db]
                    spectrum_n = np.dot(
                        histo_E_n, Gamma_n
                    )  # np.dot : method used for the spectrum computation BUT, can be optimised ???
                    treated_array_n[:, z, y, x] = spectrum_n

# Create a new ITK image from the treated array
gamma_array += treated_array_p + treated_array_n
itk_output = itk.image_from_array(treated_array_p)
itk_output.CopyInformation(img_p)
if MJ:
    itk.imwrite(itk_output, path.output / f"VPG_{File_name}_merged_prot_e.nii.gz")
else:
    itk.imwrite(itk_output, path.output / f"VPG_{File_name}_0_prot_e.nii.gz")
if neutr:
    itk_output = itk.image_from_array(treated_array_n)
    itk_output.CopyInformation(img_n)
    if MJ:
        itk.imwrite(itk_output, path.output / f"VPG_{File_name}_merged_prot_e.nii.gz")
    else:
        itk.imwrite(itk_output, path.output / f"VPG_{File_name}_0_neutr_e.nii.gz")

itk_output = itk.image_from_array(gamma_array)
if MJ:
    itk.imwrite(itk_output, path.output / f"VPG_{File_name}_merged_gamma_e.nii.gz")
else:
    itk.imwrite(itk_output, path.output / f"VPG_{File_name}_0_gamma_e.nii.gz")
