#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import itk
import uproot
import hist
import opengate as gate
import xraylib
import periodictable
from opengate.tests import utility
from opengate.definitions import elements_name_symbol
import os
import numpy as np
from test_088_vpg_tle_script import *
from test_088_multijobs import DEFAULT_OUTPUT, DEFAULT_FILE_NAME, DEFAULT_NUMBER_OF_PARTICLES, DEFAULT_ACTOR

gcm3 = gate.g4_units.g_cm3

class tle_sim:
    def __init__(self, sim, ct, actor, source):
        paths = utility.get_default_test_paths(__file__, output_folder=DEFAULT_OUTPUT)
        self.path = paths
        self.sim = sim
        self.ct = ct
        self.vpg_actor = actor
        f1 = str(paths.data / "Schneider2000MaterialsTable.txt")
        f2 = str(paths.data / "Schneider2000DensitiesTable.txt")
        tol = 0.05 * gcm3
        (voxel_materials,materials,) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
        (mat_fraction,el) = gate.geometry.materials.HU_read_materials_table(f1)
        mat_fraction.pop()
        database_mat = gate.geometry.materials.write_material_database(sim, materials, str(paths.data/"database.db"))
        self.mat_fraction = mat_fraction
        self.voxel_mat = voxel_materials
        self.el = el
        self.database_mat = database_mat
        p = os.path.abspath(str(paths.data/"database.db"))
        self.data_way = p
        f3 = str(paths.data / "data_merge.root")
        f4 = str(paths.data / "data_merge_neutron.root")
        self.root_file = uproot.open(f3)
        self.root_file_neutron = uproot.open(f4)
        

    def redim(self, ind, ct, actor_vol, array): #to convert the index from the actor volume to the ct volume
        ct_trans = list(ct.translation) # centre du ct
        vol_trans = list(actor_vol.translation)
        #passer du centre au côtés droit voxel
        ct_size = list(array.shape) # size du ct
        ct_size = array.shape
        ct_space = list(ct.spacing)
        ct_len = ct_size[0] * ct_space[0]
        ct_wid = ct_size[1] * ct_space[1]
        ct_hig = ct_size[2] * ct_space[2]
         # côté droit du vol
        x_center = ct_trans[2] - ct_len / 2
        y_center = ct_trans[1] - ct_wid / 2
        z_center = ct_trans[0] - ct_hig / 2
        #distance entre le centre du ct et le centre du vol
        decal = [vol_trans[0] - x_center, vol_trans[1] - y_center, vol_trans[2] - z_center]
        #calculer la position du voxel dans le vol
        X = ind[0] * actor_vol.spacing[0] 
        Y = ind[1] * actor_vol.spacing[1]
        Z = ind[2] * actor_vol.spacing[2]
        #calculer la position du voxel dans le ct
        x = (X + decal[0]) / ct_space[0]
        y = (Y + decal[1]) / ct_space[1]
        z = (Z + decal[2]) / ct_space[2]
        return int(x), int(y), int(z)
    
    def find_emission_vector(self, el, root_data, prot):
        if el == "Phosphor" :
            el = "Phosphorus"
        el = elements_name_symbol[el]
        if prot :
            histo = root_data[el]["PGs energy as a function of protons and GAMMAZ"].to_hist()
        else:
            histo = root_data[el]["PGs energy as a function of neutrons and GAMMAZ"].to_hist()
        w = histo.to_numpy()[0]
        return w
    
    def density_mat(self, mat, data_way):
        with open(data_way, "r") as f:
            mat = mat + ":"
            for line in f:
                words = line.split()
                if len(words) < 1 :
                    continue
                if words[0] == mat :
                    rho = words[1]
                    if words[2] == "mg/cm3;" :
                        return float(rho[2:]) / 1000 #to convert the mg/cm3 to g/cm3
                    return float(rho[2:])
        return "DEFAULT"
    
    def voxel_to_mat_name(self, UH, mat_data):
        ind = 0
        for l in mat_data :
            ind = ind + 1
            if ind == len(mat_data):
                mat = l[2]
            if UH > l[1] : 
                continue
            else : 
                mat = l[2]
                break   
        return mat #str
    
    def mat_to_UH(self, mat, mat_data):
        mat = mat.lower()
        for l in mat_data:
            print(l[2])
            if l[2] == mat.capitalize():
                return l[0]
        return "DEFAULT"
    
    def liste_el_frac(self, mat,frac_data):
        if mat[-3] == "_":
            mat = mat[:-3]
        else : 
            mat = mat[:-2]
        liste = []
        frac = []
        for l in frac_data:
            if l["name"] == mat :
                for el in l:
                    if ((el != "HU") and (el != "name")):
                        if l[el] != 0.0 :
                            liste.append(el)
                            frac.append(l[el])
        return liste, frac

    def Volume_to_array(self, vol, actor):
        size = vol.size
        spacing = actor.spacing
        array_el = np.empty((int(size[0]/spacing[0]), int(size[1]/spacing[0]), int(size[2]/spacing[0])), dtype=object)
        array_el.fill(vol.material) #fill the array with the material of the volume
        return array_el #3D array

    def gamma_mat(self, UH, root_data, prot):
        Gamma = np.zeros((500, 250))  # Initialize a 2D array for gamma emission
        """Find the material and its composition corresponding to the Hounsfield Unit (UH)"""
        name = self.voxel_to_mat_name(UH, self.voxel_mat)
        rho_mat = self.density_mat(name, self.data_way)
        (elements, fractions) = self.liste_el_frac(name, self.mat_fraction) 
        """        elements: list of elements in the material"""
        for el in elements:
            w = fractions[elements.index(el)] / 100 # Convert percentage to fraction
            vect = self.find_emission_vector(el, root_data, prot)
            Gamma += vect * w * rho_mat
        return Gamma


