import uproot
import numpy as np

case = "proton"
# Open the source ROOT file (data_merge_neutron.root) and extract the histogram
source_file = uproot.open("data/data_merge_" + case + ".root")

elements_A = ["standard_Weight","Al", "Ar", "Be","B", "Ca","C","Cl","Cu","F","He", "H","Li"]
elements_B = ["Mg","Ne","N","O","P","K","Si","Ag","Na","S","Sn","Ti","Zn"]

if case == "neutron":
    quantity = ["GammaZ", "Kapa inelastique", "NrPG", "EnEpg"]
else :
    quantity = ["GammaZ", "Kapa inelastique", "NrPG", "EpEpg"]

# Fichiers de sortie
output_A = uproot.recreate("data/data_" + case + "_A.root")
output_B = uproot.recreate("data/data_" + case + "_B.root")

for el in elements_A:
    if el == "standard_Weight":
        q = "Weight"
        key = f"{el}/{q}"
        obj = source_file[key]
        bin_contents = obj.values()
        edges_x = obj.axis(0).edges()
        output_A[key] = (bin_contents, edges_x)        
        continue       
    for q in quantity:
        # Check if the object is a histogram (TH1D or TH2D)
        key = f"{el}/{q}"
        obj = source_file[key]
        if isinstance(obj, uproot.models.TH.Model_TH2D_v4):
                # Copy other TH2D histograms as they are
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            edges_y = obj.axis(1).edges()
            output_A[key] = (bin_contents, (edges_x, edges_y))
        elif isinstance(obj, uproot.models.TH.Model_TH1D_v3):
            # Handle TH1D histograms
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            output_A[key] = (bin_contents, edges_x)

for el in elements_B:
    for q in quantity:
        # Check if the object is a histogram (TH1D or TH2D)
        key = f"{el}/{q}"
        obj = source_file[key]
        if isinstance(obj, uproot.models.TH.Model_TH2D_v4):
                # Copy other TH2D histograms as they are
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            edges_y = obj.axis(1).edges()
            output_B[key] = (bin_contents, (edges_x, edges_y))
        elif isinstance(obj, uproot.models.TH.Model_TH1D_v3):
            # Handle TH1D histograms
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            output_B[key] = (bin_contents, edges_x)
