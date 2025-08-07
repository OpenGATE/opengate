import numpy as np
import glob
import os
import SimpleITK as sitk
import uproot
import hist


Path = "/sps/creatis/vguittet/geant-stage0/output"
folders = [d for d in glob.glob(os.path.join(Path, "*/"))]
Norm = len(folders)
case = "output_507312_"
print(Norm)
    # recover all the mha files
listofFiles = glob.glob(Path + "/" + case + "*/neutr-data.root", recursive=True)
Norm = len(folders)

X = np.linspace(0, 200, 501)
Y = np.linspace(0, 10, 251)

elements = ["standard_Weight","Al", "Ar", "Be","B", "Ca","C","Cl","Cu","F","He",
"H","Li","Mg","Ne","N","O","P","K",
"Si","Ag","Na","S","Sn","Ti","Zn"]
quantity = ["GammaZ", "Kapa inelastique", "NrPG", "EnEpg"]

def accumulation(el, q):
    if q == "GammaZ" or q == "EnEpg" : 
        mega = np.zeros((500,250))
    else : 
        mega = np.zeros(500)
    for rootFile in listofFiles:
        img = uproot.open(rootFile)
        if (q == "GammaZ" or q == "EnEpg") : 
            arr, x, y =img[el][q].to_hist().to_numpy()
        else:
            arr, x =img[el][q].to_hist().to_numpy()
        mega += arr / Norm
        #vider l'arr
    return mega



 # concatenation of the data
with uproot.recreate("data_merge.root") as f:
    for el in elements :
        if el == "standard_Weight" :
            somme = accumulation(el, "Weight")
            histo_data = hist.Hist(
                    hist.axis.Variable(X, name="Neutrons Energy (MeV)"),
                    storage=hist.storage.Double(),
                )
            histo_data[...] = somme
            f[f"{el}/Weight"] = histo_data
            print(el)
            continue
        for q in quantity :
            print(el,q)
            somme = accumulation(el, q)
            if q == "GammaZ" or q == "EnEpg" :
                histo_data = hist.Hist(
                    hist.axis.Variable(X, name="Neutrons Energy (MeV)"),
                    hist.axis.Variable(Y, name="PGs energy [MeV]"),
                    storage=hist.storage.Double(),
                )
                histo_data[...] = somme
                f[f"{el}/{q}"] = histo_data
            else : 
                histo_data = hist.Hist(
                    hist.axis.Variable(X, name="Neutrons Energy (MeV)"),
                    storage=hist.storage.Double(),
                )
                histo_data[...] = somme   
                f[f"{el}/{q}"] = histo_data
            

