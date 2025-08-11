import itk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

dossier = 'patient'
part ='prot'
X = 62
Y = 66
Z = 94
case = 'try'
# Read input image
itk_image = itk.imread("output/" + dossier + "/tle_patient_0_"+ part + "_tof.nii.gz")
# Copy of itk.Image, pixel data is copied
array = itk.array_from_image(itk_image)
# Read input image
itk_image = itk.imread("output/" + dossier + "/ana_patient_0_"+ part + "_tof.nii.gz")
# Copy of itk.Image, pixel data is copied
ana_array = itk.array_from_image(itk_image)
N = 1e7

ana_histogram = np.zeros(ana_array.shape[0])
ana_histogram = ana_array[:, Z, Y, X]
#ana_histogram = ana_histogram[:-1]

histogram = np.zeros(array.shape[0])
histogram = array[:, Z, Y, X]

ana_norma = np.sum(ana_histogram)
norma=np.sum(histogram)

ana_histogram = ana_histogram / ana_norma
histogram = histogram / norma

inc = np.sqrt(ana_histogram/N)
inc = inc / ana_norma
print(max(inc))

# Define the energy axis (assuming the histogram bins correspond to energy levels)
energy_axis = np.linspace(0, 5, len(ana_histogram))  # Adjust the range and number of bins as needed
 
# Plot the histogram
plt.figure(figsize=(10, 6))
plt.plot(energy_axis, ana_histogram, label=f"analog MC" , color="red", linewidth=1)
plt.plot(energy_axis, histogram, label=f"vpgtle MC" , color="green", linewidth=1)

# Add labels, title, and grid
plt.xlabel("Time of flight (ns)", fontsize=14)
plt.ylabel("PG yield / 20 ps / protons", fontsize=14)
if part == "prot":
    plt.xlim(0, 5)
else :
    plt.xlim(0, 5)
# Enable minor ticks for a more precise grid
plt.minorticks_on()
plt.title(f"PG emission probability depending on " + part + "ons ToF [" + str(Y * 4) + " mm]", fontsize=16)

# Customize the grid
plt.grid(which="major", linestyle="-", linewidth=0.8, alpha=0.8)  # Major grid lines
plt.grid(which="minor", linestyle=":", linewidth=0.5, alpha=0.5)  # Minor grid lines
plt.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))

# Add a legend
plt.legend(fontsize=12)
plt.savefig("output/" + dossier + "/ToF_" + part + "on_" + case + ".pdf", dpi=300, format="pdf", bbox_inches='tight')
# Show the plot

plt.show()