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
    itk_output = itk.image_from_array(Gamma)
    itk.imwrite(itk_output, paths.output / f"{name}.nii.gz")

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

    # features of simulation that can be modify
    output = "stage1a"
    File_name = "vpg"
    vol_name = "ct"
    MJ = False
    number_of_particles = 1e6
    # source Energy andrange of the actor
    Erange = 130
    
    paths = utility.get_default_test_paths(__file__, output_folder="test081_pgtle")
    #paths = Box()
    # data and output are in the parent directory
    #paths.current = pathlib.Path().resolve().parent
    #paths.data = (paths.current / "data").resolve()
    #paths.output = (paths.current / "output" / output).resolve()

    job_id = 0
    visu = False

    # paths = utility.get_default_test_paths(__file__, gate_folder="", output_folder=output)          
    # create the simulation
    sim = gate.Simulation()
    # main options
    sim.visu = visu
    sim.g4_verbose = False
    sim.random_seed = "auto"  # FIXME to be replaced by a fixed number at the end
    sim.random_engine = "MersenneTwister"
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.progress_bar = True

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
    """
    ct = sim.add_volume("Image", "ct")
    ct.image = paths.data / f"1mm-carbo-volume.mhd"
    if visu :
        ct.image = paths.data / f"visu-carbo-volume.mhd"
    ct.mother = "world"
    ct.material = "G4_C"
    ct.voxel_materials = [
    # range format [)
    [-2000, -700, "G4_C"],
    ]
    ct.dump_label_image = "labels.mhd"
    """

    ct = sim.add_volume("Image", vol_name)
    ct.image = paths.data / "test081_pgtle" / f"ct_4mm.mhd"
    if sim.visu:
        ct.image = paths.data / f"ct_40mm.mhd"
    ct.material = "G4_AIR"
    #f1 = paths.data / "test081_pgtle" / "Schneider2000MaterialsTable.txt"
    #f2 = paths.data / "test081_pgtle" / "Schneider2000DensitiesTable.txt"
    f1 = paths.data / "test081_pgtle" / "OxygenMaterialsTable.txt"
    f2 = paths.data / "test081_pgtle" / "UnitDensitiesTable.txt"
    tol = 0.05 * gcm3
    (ct.voxel_materials, materials,) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)

    (mat_fraction, el) = gate.geometry.materials.HU_read_materials_table(f1)
    database_mat = gate.geometry.materials.write_material_database(sim, materials, paths.output / "database.db")

    ct.dump_label_image = paths.output / f"labels.mhd"
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
    with uproot.open(paths.data / "test081_pgtle" / "data_merge_proton.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_p = histo.to_numpy()[0]
    with uproot.open(paths.data  / "test081_pgtle" / "data_merge_neutron.root") as root_file:
        histo = root_file["standard_Weight"]["Weight"].to_hist()
        vect_n = histo.to_numpy()[0]

    vpg_tle = sim.add_actor("VoxelizedPromptGammaTLEActor", "vpg_tle")
    vpg_tle.attached_to = vol_name
    vpg_tle.output_filename = f"{File_name}.nii.gz"
    vpg_tle.size = [125, 125, 189]  # the same size than ct image is stronly adviced
    vpg_tle.spacing = [4, 4, 4, ]  # the same spacing is stronly adviced
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

    analog_tle = sim.add_actor("VoxelizedPromptGammaAnalogActor", "analog_tle")
    analog_tle.attached_to = vol_name
    analog_tle.output_filename = f"{File_name}_analog.nii.gz"
    analog_tle.size = [125, 125, 189]  # the same size than ct image is stronly adviced
    analog_tle.spacing = [4, 4, 4, ]  # the same spacing is stronly adviced
    analog_tle.timebins = 250
    analog_tle.timerange = 5 * ns
    analog_tle.energybins = 250
    analog_tle.energyrange = 10 * MeV
    analog_tle.prot_E.active = True
    analog_tle.neutr_E.active = True
    analog_tle.prot_tof.active = True
    analog_tle.neutr_tof.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = f"stat_{job_id}_{File_name}.txt"

    sim.run()
    
    #print(stats)
    #print()

    
    ######## Track Length => PG energy ########################################################

    # FIRST STEP : retrieve the arrays and all the needed features

    # CT volume :
    UH_array = itk.array_from_image(ct.load_input_image())
    # database
    data_protons = uproot.open(paths.data / "test081_pgtle" / "data_merge_proton.root")
    data_neutrons = uproot.open(paths.data / "test081_pgtle" / "data_merge_neutron.root")
    mat = ct.voxel_materials

    # SECOND STEP : compute the material Gamma for each materials present in the ct and store it in a list

    neutr = False  # to skip step if neutron are not taking into account
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

    if MJ:  # multijobs or not ??
        img_p = itk.imread(paths.output / f"{File_name}_merged_prot_e.nii.gz")
    else:
        img_p = itk.imread(paths.output / f"{File_name}_prot_e.nii.gz")
    array_p = itk.array_from_image(img_p)
    
    if neutr:
        if MJ:
            img_n = itk.imread(paths.output / f"{File_name}_merged_neutr_e.nii.gz")
        else:
            img_n = itk.imread(paths.output / f"{File_name}_neutr_e.nii.gz")
        array_n = itk.array_from_image(img_n)

    # Initialize the treated array for proton, neutron, and proton + neutron
    treated_array_p = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))  
    treated_array_n = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))
    gamma_array = np.zeros((250, array_p.shape[1], array_p.shape[2], array_p.shape[3]))

    # Vectorized processing: map actor voxel indices to CT indices, group by material
    E, Nz, Ny, Nx = array_p.shape

    # Build CT material lookup (map unique HU values once)
    valid_hu = UH_array != -3024
    hu_values = np.unique(UH_array[valid_hu])
    hu_to_mat = {}
    for hu in hu_values:
        hu_to_mat[hu] = voxel_to_mat_name(int(hu), mat)

    material_array = np.empty(UH_array.shape, dtype=object)
    for hu, mname in hu_to_mat.items():
        material_array[UH_array == hu] = mname

    # Create actor-coordinate grids
    inds = np.indices((Nz, Ny, Nx), dtype=int)
    z_idx, y_idx, x_idx = inds[0], inds[1], inds[2]

    # Vectorized coordinate transformation (redim)
    if ct.size == vpg_tle.size:
        x_ct, y_ct, z_ct = x_idx, y_idx, z_idx
    else:
        ct_trans = list(ct.translation)
        vol_trans = list(vpg_tle.translation)
        decal = [vol_trans[2] - ct_trans[2], vol_trans[1] - ct_trans[1], vol_trans[0] - ct_trans[0]]
    
        X = x_idx * vpg_tle.spacing[2]
        Y = y_idx * vpg_tle.spacing[1]
        Z = z_idx * vpg_tle.spacing[0]
    
        x_ct = np.floor((X + decal[0]) / ct.spacing[0]).astype(int)
        y_ct = np.floor((Y + decal[1]) / ct.spacing[1]).astype(int)
        z_ct = np.floor((Z + decal[2]) / ct.spacing[2]).astype(int)

    # Clip to valid ranges
    x_ct = np.clip(x_ct, 0, UH_array.shape[2] - 1)
    y_ct = np.clip(y_ct, 0, UH_array.shape[1] - 1)
    z_ct = np.clip(z_ct, 0, UH_array.shape[0] - 1)

    # Valid voxels
    valid_mask = UH_array[z_ct, y_ct, x_ct] != -3024

    # Flatten for batch operations
    N = Nz * Ny * Nx
    Hp = array_p.reshape(E, N)
    if neutr:
        Hn = array_n.reshape(E, N)
    valid_flat = valid_mask.ravel(order='C')
    mat_flat = material_array[z_ct, y_ct, x_ct].ravel(order='C')

    # Process by material using batched matrix multiply
    for mat_name in np.unique(mat_flat[valid_flat]):
        if mat_name is None:
            continue
        sel = (mat_flat == mat_name) & valid_flat
        if not np.any(sel):
            continue
        cols = np.nonzero(sel)[0]
    
        Hp_sel = Hp[:, cols].T  # (n_voxels, E)
    
        # Proton
        Gamma_p = gamma_proton[mat_name][ind_db]
        if Hp_sel.size > 0:
            S_p = Hp_sel.dot(Gamma_p)
            z_flat, y_flat, x_flat = np.unravel_index(cols, (Nz, Ny, Nx))
            for i in range(len(cols)):
                treated_array_p[:, z_flat[i], y_flat[i], x_flat[i]] = S_p[i]
    
        # Neutron
        if neutr:
            Hn_sel = Hn[:, cols].T  # (n_voxels, E)
            Gamma_n = gamma_neutron[mat_name][ind_db]
            if Hn_sel.size > 0:
                S_n = Hn_sel.dot(Gamma_n)
                z_flat, y_flat, x_flat = np.unravel_index(cols, (Nz, Ny, Nx))
                for i in range(len(cols)):
                    treated_array_n[:, z_flat[i], y_flat[i], x_flat[i]] = S_n[i]
                    
    # Create a new ITK image from the treated array
    gamma_array += treated_array_p + treated_array_n
    itk_output = itk.image_from_array(treated_array_p)
    itk_output.CopyInformation(img_p)
    if MJ:
        itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_merged_prot_e.nii.gz")
    else:
        itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_prot_e.nii.gz")
    if neutr:
        itk_output = itk.image_from_array(treated_array_n)
        itk_output.CopyInformation(img_n)
        if MJ:
            itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_merged_neutr_e.nii.gz")
        else:
            itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_neutr_e.nii.gz")

    itk_output = itk.image_from_array(gamma_array)
    if MJ:
        itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_merged_gamma_e.nii.gz")
    else:
        itk.imwrite(itk_output, paths.output / f"VPG_{File_name}_gamma_e.nii.gz")

    # check outputs
    #img1 = itk.imread(analog_tle.get_output_path())
    #img2 = itk.imread(vpg_tle.get_output_path())

    #print(sum(im1))
    #print(sum(im2))
    
    #utility.test_ok(is_ok)
