#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uproot
import opengate as gate
from opengate.tests import utility
from opengate.definitions import elements_name_symbol
import os
import numpy as np
from stage_1a import *

gcm3 = gate.g4_units.g_cm3

class tle_sim:
    def __init__(self, sim):
        paths = utility.get_default_test_paths(__file__, output_folder=output)
        self.path = paths
        self.sim = sim
        self.ct = sim.volume_manager.volumes["ct"]
        self.act = sim.actor_manager.actors["vpg_tle"]
        actors_list = []
        if self.act.prot_E.active:
            actors_list.append("prot_e.nii.gz")
        if self.act.neutr_E.active:
            actors_list.append("neutr_e.nii.gz")
        self.actor_list = actors_list
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
        f3 = str(paths.data / "data_merge_proton.root")
        f4 = str(paths.data / "data_merge_neutron.root")
        self.root_file = uproot.open(f3)
        self.root_file_neutron = uproot.open(f4)
        

    def redim(self, ind, ct, actor_vol, array): #to convert the index from the actor volume to the ct volume
        
        #centres ct et actor
        ct_trans = list(ct.translation) 
        vol_trans = list(actor_vol.translation)

        #distance entre le centre du ct et le centre du vol
        decal = [vol_trans[2] - ct_trans[2], vol_trans[1] - ct_trans[1], vol_trans[0] - ct_trans[0]]

        #calculer la position du voxel dans le volume de l'actor
        X = ind[0] * actor_vol.spacing[2] 
        Y = ind[1] * actor_vol.spacing[1]
        Z = ind[2] * actor_vol.spacing[0]

        #calculer la position du voxel dans le ct
        x = (X + decal[0]) / ct.spacing[0]
        y = (Y + decal[1]) / ct.spacing[1]
        z = (Z + decal[2]) / ct.spacing[2]

        return int(x), int(y), int(z)
    
    def find_emission_vector(self, el, root_data):
        if el == "Phosphor" :
            el = "Phosphorus"
        el = elements_name_symbol[el]
        histo = root_data[el]["GammaZ"].to_hist()
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

    def gamma_mat(self, name, root_data):
        Gamma = np.zeros((500, 250))  # Initialize a 2D array for gamma emission
        """Find the material and its composition corresponding to the Hounsfield Unit (UH)"""
        rho_mat = self.density_mat(name, self.data_way)
        
        (elements, fractions) = self.liste_el_frac(name, self.mat_fraction) 
        """        elements: list of elements in the material"""
        for el in elements:
            w = fractions[elements.index(el)] / 100 # Convert percentage to fraction
            vect = self.find_emission_vector(el, root_data)
            Gamma += vect * w * rho_mat
        return Gamma


