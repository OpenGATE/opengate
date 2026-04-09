#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.definitions import elements_name_symbol

import uproot

from box import Box
import numpy as np

import itk
import hist

import time
import glob

def redim(ind, ct, actor_vol, array):  # to convert the index from the actor volume to the ct volume

    # centres ct et actor
    ct_trans = list(ct.translation)
    vol_trans = list(actor_vol.translation)

    # distance entre le centre du ct et le centre du vol
    decal = [
        vol_trans[2] - ct_trans[2],
        vol_trans[1] - ct_trans[1],
        vol_trans[0] - ct_trans[0],
    ]

    # calculer la position du voxel dans le volume de l'actor
    X = ind[0] * actor_vol.spacing[2]
    Y = ind[1] * actor_vol.spacing[1]
    Z = ind[2] * actor_vol.spacing[0]

    # calculer la position du voxel dans le ct
    x = (X + decal[0]) / ct.spacing[0]
    y = (Y + decal[1]) / ct.spacing[1]
    z = (Z + decal[2]) / ct.spacing[2]

    return int(x), int(y), int(z)


def find_emission_vector(el, root_data):  # to find the TH2D in the root_data corresponding to the element el
    #if el == "Phosphor":
    #    el = "Phosphorus"
    el = elements_name_symbol[el]
    histo = root_data[el]["GammaZ"].to_hist()
    w = histo.to_numpy()[0]
    return w

def liste_el_frac(mat, frac_data):  # from material, extract a list of element and a list of fraction. Element and its corresponding fraction are stored with the same index in both lists
    if mat[-3] == "_":
        mat = mat[:-3]
    else:
        mat = mat[:-2]
    liste = []
    frac = []
    for l in frac_data:
        if l["name"] == mat:
            for el in l:
                if (el != "HU") and (el != "name"):
                    if l[el] != 0.0:
                        liste.append(el)
                        frac.append(l[el])
    return liste, frac


def density_mat(mat, data_way):  # read the datas to find the density of the material
    with open(data_way, "r") as f:
        mat = mat + ":"
        for line in f:
            words = line.split()
            if len(words) < 1:
                continue
            if words[0] == mat:
                rho = words[1]
                if words[2] == "mg/cm3;":
                    return float(rho[2:]) / 1000  # to convert the mg/cm3 to g/cm3
                return float(rho[2:])
    return "DEFAULT"

def gamma_mat(paths, mat_fraction, name, root_data):  # construct the GammaZ corresponding to the material
    Gamma = np.zeros((500, 250))  # Initialize a 2D array for gamma emission

    """Find the material and its composition corresponding to the Hounsfield Unit (UH)"""
    data_way = paths.output / "database.db"
    rho_mat = density_mat(name, data_way)
    (elements, fractions) = liste_el_frac(name, mat_fraction)

    """        elements: list of elements in the material"""
    for el in elements:
        w = fractions[elements.index(el)] / 100  # Convert percentage to fraction
        vect = find_emission_vector(el, root_data)
        Gamma += vect * w * rho_mat

    # dump material DB
    #itk_output = itk.image_from_array(Gamma)
    #itk.imwrite(itk_output, paths.output / f"{name}.nii.gz")

    return Gamma

def voxel_to_mat_name(UH, mat_data):  # from UH to material name
    ind = 0
    for l in mat_data:
        ind = ind + 1
        if ind == len(mat_data):
            mat = l[2]
        if UH > l[1]:
            continue
        else:
            mat = l[2]
            break
    return mat  # str


if __name__ == "__main__":

    np.seterr(all='raise')

    # features of simulation that can be modify
    file_name = "stage1_vpg"
    vol_name = "ct"
    number_of_particles = 1e6
    # source Energy andrange of the actor
    Erange = 130
    test_name="test081_pgtle"
    paths = utility.get_default_test_paths(__file__, output_folder=test_name)

    #def get_default_test_paths(f, gate_folder=None, output_folder=None):
    #
    #    paths = utility.get_default_test_paths(
    #    __file__, "gate_test042_gauss_gps", "test008"
    #)
    # gives
    #{'current': PosixPath('/home/letang/opengate/opengate/tests/src'), 
    # 'data': PosixPath('/home/letang/opengate/opengate/tests/data'), 
    # 'gate': PosixPath('/home/letang/opengate/opengate/tests/data/gate/gate_test042_gauss_gps'), 
    # 'gate_output': PosixPath('/home/letang/opengate/opengate/tests/data/gate/gate_test042_gauss_gps/output'), 
    # 'gate_data': PosixPath('/home/letang/opengate/opengate/tests/data/gate/gate_test042_gauss_gps/data'), 
    # 'output': PosixPath('/home/letang/opengate/opengate/tests/output/test008'), 
    # 'output_ref': PosixPath('/home/letang/opengate/opengate/tests/data/output_ref/test008')}

    job_id = 0
    visu = False

    # create the simulation
    sim = gate.Simulation()
    # main options
    sim.visu = visu
    sim.g4_verbose = False
    sim.random_seed = "auto"  # FIXME to be replaced by a fixed number at the end
    sim.random_engine = "MersenneTwister"
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.progress_bar = False

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    MeV = gate.g4_units.MeV
    ns = gate.g4_units.ns
    gcm3 = gate.g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_Galactic"

    # patient

    ct = sim.add_volume("Image", vol_name)
    ct.image = paths.data / f"ct_40mm_ij.mhd"
    ct.material = "G4_AIR"
    f1 = paths.data / "Schneider2000MaterialsTable.txt"
    f2 = paths.data / "Schneider2000DensitiesTable.txt"
    tol = 0.05 * gcm3
    (ct.voxel_materials, materials,) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)


    (mat_fraction, el) = gate.geometry.materials.HU_read_materials_table(f1)
    database_mat = gate.geometry.materials.write_material_database(sim, materials, paths.output / "database.db")

    ct.dump_label_image = paths.output / f"labels.nii.gz"
    ct.mother = "world"
    ct.load_input_image()

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP_EMY"

    sim.physics_manager.apply_cuts = False  # default
    sim.physics_manager.global_production_cuts.gamma = 0.1 * mm
    sim.physics_manager.global_production_cuts.electron = 0.1 * mm
    sim.physics_manager.global_production_cuts.positron = 0.1 * mm
    sim.physics_manager.global_production_cuts.proton = 0.1 * mm

    sim.physics_manager.set_max_step_size("ct", 0.1 * mm)
    sim.physics_manager.set_user_limits_particles(["proton"])

    # source of proton
    # FIXME to replace by a more realistic proton beam, see tests 044
    source = sim.add_source("GenericSource", "DEFAULT")
    source.energy.mono = Erange * MeV
    source.particle = "proton"
    source.position.type = "point"
    source.position.radius = 1 * mm
    source.position.translation = [0 * mm, -300 * mm, 0 * mm]
    source.n = number_of_particles
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]

    # LOOKHERE :: if database not well implanted, has to be modified 
    with uproot.open(paths.data / test_name / "data_merge_proton.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_p = histo.to_numpy()[0]
    with uproot.open(paths.data  / test_name / "data_merge_neutron.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_n = histo.to_numpy()[0]

    vpg_tle = sim.add_actor("VoxelizedPromptGammaTLEActor", "vpg_tle")
    vpg_tle.attached_to = vol_name
    vpg_tle.output_filename = f"{file_name}_tle.nii.gz"
    vpg_tle.size = [13, 13, 19]  # the same size than ct image is stronly adviced
    vpg_tle.spacing = [40, 40, 40, ]  # the same spacing is stronly adviced
    vpg_tle.timebins = 250
    vpg_tle.timerange = 5 * ns
    vpg_tle.energybins = 250
    vpg_tle.energyrange = 200 * MeV
    #vpg_tle.energyrange = Erange * MeV
    vpg_tle.prot_E.active = True
    vpg_tle.neutr_E.active = True
    vpg_tle.prot_tof.active = True
    vpg_tle.neutr_tof.active = True
    vpg_tle.weight = True  # True to obtain weighted time spectra
    vpg_tle.vect_p = vect_p
    vpg_tle.vect_n = vect_n

    vpg_analog = sim.add_actor("VoxelizedPromptGammaAnalogActor", "vpg_analog")
    vpg_analog.attached_to = vol_name
    vpg_analog.output_filename = f"{file_name}_analog.nii.gz"
    vpg_analog.size = [13, 13, 19]  # the same size than ct image is stronly adviced
    vpg_analog.spacing = [40, 40, 40, ]  # the same spacing is stronly adviced
    vpg_analog.timebins = 250
    vpg_analog.timerange = 5 * ns
    vpg_analog.energybins = 250
    vpg_analog.energyrange = 10 * MeV
    vpg_analog.prot_E.active = True
    vpg_analog.neutr_E.active = True
    vpg_analog.prot_tof.active = True
    vpg_analog.neutr_tof.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = f"stat_{job_id}_{file_name}.txt"

    sim.run()
    
    print(stats)
    print()
    
    ######## Track Length => PG energy ########################################################

    # FIRST STEP : retrieve the arrays and all the needed features

    # CT volume :
    UH_array = itk.array_from_image(ct.load_input_image())
    # database
    data_protons = uproot.open(paths.data / "test081_pgtle" / "data_merge_proton.root")
    data_neutrons = uproot.open(paths.data / "test081_pgtle" / "data_merge_neutron.root")
    mat = ct.voxel_materials

    # SECOND STEP : compute the material Gamma for each materials present in the ct and store it in a list

    neutr = True  # to skip step if neutron are not taking into account
    if vpg_tle.neutr_E.active:
        neutr = True
    gamma_neutron = {}
    gamma_proton = {}
    # building a dico that links for each mterial name, the Gamma histograms
    for data in mat:
        name = data[2]
        if neutr:
            gamma_neutron[name] = gamma_mat(paths, mat_fraction, name, data_neutrons)
        gamma_proton[name] = gamma_mat(paths, mat_fraction, name, data_protons)

    # THIRD STEP : convert the energy histogram stored the 4D output into emission spectra for each voxel of the ct volume
    Ep = np.linspace(0, vpg_tle.energyrange, vpg_tle.energybins + 1)
    E_db = np.linspace(0, 200, 500)
    ind_db = np.abs(E_db[None, :] - Ep[:, None]).argmin(axis=1) # LOOKHERE :: should find a better way to build the index list

    img_p = itk.imread(paths.output / f"{file_name}_tle_prot_e.nii.gz")
    array_p = itk.array_from_image(img_p)
    
    if neutr:
        img_n = itk.imread(paths.output / f"{file_name}_tle_neutr_e.nii.gz")
        array_n = itk.array_from_image(img_n)

    # Initialize the treated array for proton, neutron, and proton + neutron
    treated_array_p = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))  
    treated_array_n = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))
    gamma_array = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))


    # treatment of the image voxel by voxel => to store gamma emission spectrum in each voxel
    for x in range(array_p.shape[3]):
        for y in range(array_p.shape[2]):
            for z in range(array_p.shape[1]):
                # Get the Hounsfield Unit (HU) value at the current voxel
                if ct.size == vpg_tle.size:
                    # If the CT size matches the actor size, use the voxel coordinates directly
                    X, Y, Z = x, y, z
                else:
                    X, Y, Z = redim((x, y, z), ct, vpg_tle, array_p)
                if (
                    UH_array[Z, Y, X] == -3024
                ):  # LOOKHERE : conditions of the CT where there is no matter, to be removed if CT different from the exemple case
                    # Skip the voxel if HU value is -3024
                    continue
                name = voxel_to_mat_name(UH_array[Z, Y, X], ct.voxel_materials)
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
    itk_output = itk.image_from_array(treated_array_p)
    itk_output.CopyInformation(img_p)
    itk.imwrite(itk_output, paths.output / f"{file_name}_tle_prot_pge.nii.gz")
    if neutr:
        itk_output = itk.image_from_array(treated_array_n)
        itk_output.CopyInformation(img_n)
        itk.imwrite(itk_output, paths.output / f"{file_name}_tle_neutr_pge.nii.gz")

    # tests (neutron, proton) x (E,tof)

    #utility.test_ok(is_ok)
