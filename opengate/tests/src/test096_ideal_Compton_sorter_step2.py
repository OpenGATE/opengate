#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.coincidences import ccmod_ideal_coincidences
from opengate.actors.coincidences import ccmod_make_cones
from scipy.stats import wasserstein_distance
import uproot
import os
import numpy as np
import sys
import pandas as pd




def main(dependency="test096_coinc_sorter_step1.py"):

    # If output_singles.root does not exist, run a simulation to generate it
    paths = utility.get_default_test_paths(__file__, output_folder="test096")
    root_filename = paths.output / "PhaseSpace.root"
    if not os.path.exists(root_filename):
        print(f"Simulating PhSp to create {root_filename} ...")
        os.system(f"python {str(paths.current / dependency)}")

    
    root_file = uproot.open(root_filename)
    phSp_tree = root_file["PhaseSpace"]
    n = int(phSp_tree.num_entries)
    print(f"There are {n} hits saved")
    # save it into pandas data frame
    data = phSp_tree.arrays(library="pd")



    data_coinc = ccmod_ideal_coincidences(data)
    data_cones = ccmod_make_cones(data_coinc)
    

    #compare cones from GATE9 and from GATE10
    # Compare with reference output
    
    ref_folder = paths.output_ref
    print(ref_folder)
    ref_filename = ref_folder / "CC_idealprocessing_Singles.root"
    file = uproot.open(ref_filename)
    Sn = file['Singles']
    data_GATE9 = Sn.arrays(library="pd")
    data_GATE9 = data_GATE9.drop(columns=["layerName"])#To avoid warning coming from conversion to pd
    data_GATE9 = data_GATE9.drop(columns=["volumeID"])#To avoid warning coming from conversion to pd
    
    data_GATE9["IdealTotalEnergyDeposit"] = data_GATE9["energyIni"] - data_GATE9["energyFinal"] 
    #by hand since different  attribute names and pre-processing
    nSingles = data_GATE9["eventID"].value_counts()
    #keep only events with more than one nSingles
    data_GATE9 = data_GATE9[data_GATE9["eventID"].isin(nSingles[nSingles > 1].index)]
    data_GATE9["CoincID"] = pd.factorize(data_GATE9["eventID"])[0] 
    
    data_cones_GATE9 = ccmod_make_cones(data_GATE9,energy_key_name = "IdealTotalEnergyDeposit", posX_key_name ="globalPosX",posY_key_name = "globalPosY",posZ_key_name = "globalPosZ")


   
    distance_energy = wasserstein_distance(data_cones["Energy1"],data_cones_GATE9["Energy1"])
    
    #Faire un moyen de la energy et l'energy max pour le tst. wher I have Cpmtpo So I know tha max for my energy 
    #tolerance_energy = 0.005
    #print(
    #    f"Wasserstein distance on energy : {distance_energy}, tolerence {tolerance_energy}"
    #)
    
    
    
   


if __name__ == "__main__":
    main()
