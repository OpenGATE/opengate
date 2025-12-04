import itk
import numpy as np
import matplotlib.pyplot as plt
import uproot

dossier = "patient"
part = "prot"
X = 62
Y = 66
Z = 94
case = "try"
# Read input image
itk_image = itk.imread(
    "output/" + dossier + "/optiVPG_tle_patient_0_" + part + "_e.nii.gz"
)
# Copy of itk.Image, pixel data is copied
array = itk.array_from_image(itk_image)

# Read input image
itk_image = itk.imread("output/" + dossier + "/ana_patient_0_" + part + "_e.nii.gz")
# Copy of itk.Image, pixel data is copied
ana_array = itk.array_from_image(itk_image)
N = 1e7

histogram = np.zeros(array.shape[0])
ana_histogram = np.zeros(ana_array.shape[0])
ana_histogram = ana_array[:, Z, Y, X]
histogram = array[:, Z, Y, X]

ana_histogram = ana_histogram[:-1]
inc = np.sqrt(ana_histogram / N)

energy_axis = np.linspace(0, 10, len(ana_histogram))
# Plot the histogram
plt.figure(figsize=(10, 6))
plt.plot(energy_axis, histogram, label=f"vpgTLE MC", color="blue", linewidth=1)
plt.plot(energy_axis, ana_histogram, label=f"Analog MC", color="red", linewidth=1)
plt.fill_between(
    energy_axis,
    histogram + 3 * inc,
    histogram - 3 * inc,
    color="red",
    alpha=0.1,
    linewidth=1,
)

# Add labels, title, and grid
plt.xlabel("PG energy (MeV)", fontsize=14)
plt.ylabel("PG yield / 40 keV / " + part + "ons", fontsize=14)

# Enable minor ticks for a more precise grid
plt.minorticks_on()
plt.title(f"PG yield from " + part + "ons energy [" + str(4 * Y) + " mm]", fontsize=16)
# Customize the grid
plt.grid(which="major", linestyle="-", linewidth=0.8, alpha=0.8)  # Major grid lines
plt.grid(which="minor", linestyle=":", linewidth=0.5, alpha=0.5)  # Minor grid lines
plt.ticklabel_format(axis="y", style="sci", scilimits=(0, 0))


# Add a legend
plt.legend(fontsize=12)
plt.savefig(
    "output/" + dossier + "/Energy_" + part + "on_" + case + ".pdf",
    dpi=300,
    format="pdf",
    bbox_inches="tight",
)

# Show the plot

plt.show()
