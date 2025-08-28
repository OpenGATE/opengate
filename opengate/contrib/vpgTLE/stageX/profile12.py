#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

# Read input image
itk_image = itk.imread("output/box/map_analogu_0_prot_e.nii.gz")
spacing = itk.spacing(itk_image)
# Copy of itk.Image, pixel data is copied
array = itk.array_from_image(itk_image)

# Read input image
Nitk_image = itk.imread("output/box/map_analogu_0_neutr_e.nii.gz")
Nspacing = itk.spacing(Nitk_image)
# Copy of itk.Image, pixel data is copied
Narray = itk.array_from_image(Nitk_image)

# on stocke les dimensions de l'image
x_size = array.shape[3]
y_size = array.shape[2]
z_size = array.shape[1]
H = np.linspace(0, y_size * spacing[2] / 10, y_size)

# Create a 3D coordinate grid with proper axis handling
z, y, x = np.meshgrid(
    np.linspace(
        -z_size * spacing[1] / 20, z_size * spacing[1] / 20, z_size
    ),  # z-axis (first dimension in the array)
    np.linspace(
        0, y_size * spacing[2] / 10, y_size
    ),  # y-axis (second dimension in the array)
    np.linspace(
        -x_size * spacing[3] / 20, x_size * spacing[3] / 20, x_size
    ),  # x-axis (third dimension in the array)
    indexing="ij",  # Use 'ij' indexing to match the array's shape
)
x = x.ravel()
y = y.ravel()
z = z.ravel()

# La couleur prise par les voxels dans la vue globale se fera par rapport à la moyenne du nombre d'occurence dans les histogrammes
Narray_intensity = np.sum(Narray, axis=0)
array_intensity = np.sum(array, axis=0)

N = 1e7
Ninc = np.sqrt(Narray_intensity / N)
inc = np.sqrt(array_intensity / N)
# Define the radius and height bins
Max = np.sqrt(x[x_size - 1] ** 2 + z[z_size - 1] ** 2)
R = np.linspace(0, Max, z_size)
H = np.linspace(0, y_size * spacing[2] / 10, y_size)
theta = np.linspace(0, np.pi / 2, 100)  # Angle for cylindrical coordinates
# Initialize the graphs
graph = np.zeros((len(R)), dtype=float)
Ngraph = np.zeros((len(R)), dtype=float)

sig = np.zeros(graph.shape)
Nsig = np.zeros(Ngraph.shape)

tot = np.zeros((len(R)), dtype=float)
# Calculate the bin width
width = spacing[1] / 10
center = int(x_size / 2)  # Center index for the x-axis
dh = spacing[2] / 10
dr = width

for r in range(len(R)):
    for t in range(len(theta)):
        for h in range(y_size):
            X = int(R[r] * np.cos(theta[t]) / width)
            Z = int(R[r] * np.sin(theta[t]) / width)
            # si hors du cylindre d'intérêt (dans les coins du carré de 14 cm de côté)
            if X >= 100 or Z >= 100:
                continue
            D = R[r] + dr / 2
            quotient = 2 * np.pi * D * dr * dh
            # premier quart
            graph[r] += array_intensity[center + Z, h, center + X] / quotient
            Ngraph[r] += Narray_intensity[center + Z, h, center + X] / quotient
            sig[r] += (inc[center + Z, h, center + X] / quotient) ** 2
            Nsig[r] += (Ninc[center + Z, h, center + X] / quotient) ** 2
            # deuxième quart
            graph[r] += array_intensity[center + Z, h, center - X] / quotient
            Ngraph[r] += Narray_intensity[center + Z, h, center - X] / quotient
            sig[r] += (inc[center + Z, h, center - X] / quotient) ** 2
            Nsig[r] += (Ninc[center + Z, h, center - X] / quotient) ** 2
            # troisième quart
            graph[r] += array_intensity[center - Z, h, center - X] / quotient
            Ngraph[r] += Narray_intensity[center - Z, h, center - X] / quotient
            sig[r] += (inc[center - Z, h, center - X] / quotient) ** 2
            Nsig[r] += (Ninc[center - Z, h, center - X] / quotient) ** 2
            # quatrième quart
            graph[r] += array_intensity[center - Z, h, center + X] / quotient
            Ngraph[r] += Narray_intensity[center - Z, h, center + X] / quotient
            sig[r] += (inc[center - Z, h, center + X] / quotient) ** 2
            Nsig[r] += (Ninc[center - Z, h, center + X] / quotient) ** 2
            tot[r] = graph[r] + Ngraph[r]
R = R.ravel()
sig = np.sqrt(sig)
Nsig = np.sqrt(Nsig)
Ngraph = Ngraph.ravel()
graph = graph.ravel()
sig = sig.ravel()
Nsig = Nsig.ravel()
tot = tot.ravel()
print("min inc prot", np.min(sig))
print("max inc prot", np.max(sig))
print("min inc neut", np.min(Nsig))
print("max Ninc neutr", np.max(Nsig))
# Create a figure and axis
fig = plt.figure(figsize=(10, 6))
# Plot graph and Ngraph against R
plt.plot(R, graph, label="Protons", color="red", linewidth=1)
plt.fill_between(R, graph - 3 * sig, graph + 3 * sig, color="red", alpha=0.08)
plt.plot(R, Ngraph, label="Neutrons", color="blue", linewidth=1)
plt.fill_between(R, Ngraph - 3 * Nsig, Ngraph + 3 * Nsig, color="blue", alpha=0.08)
plt.plot(R, tot, label="total", color="black", linewidth=1, linestyle="--")
# Add labels, legend, and title
plt.xlabel("Radius (cm)", fontsize=14)
plt.ylabel("cts / protons / (cm3)", fontsize=14)
plt.title("PGs emission against the radius", fontsize=20)
plt.legend(fontsize=12)

ax = plt.gca()
# Set the y-axis to scientific notation
formatter = ScalarFormatter(useMathText=True)
formatter.set_scientific(True)
formatter.set_powerlimits((-2, 3))  # Set limits for scientific notation
ax.yaxis.set_major_formatter(formatter)

# Enable minor ticks for a more precise grid
plt.minorticks_on()

# Customize the grid
plt.grid(which="major", linestyle="-", linewidth=0.8, alpha=0.8)  # Major grid lines
plt.grid(which="minor", linestyle=":", linewidth=0.5, alpha=0.5)  # Minor grid lines
# Add more ticks to the y-axis
# plt.gca().yaxis.set_major_locator(MultipleLocator(1))  # Major ticks every 1 unit
# plt.gca().yaxis.set_minor_locator(MultipleLocator(0.2))  # Minor ticks every 0.2 units

plt.yscale("log")
plt.xlim(0, 14)
# Show the plot
plt.savefig("analogprofileradial.pdf", format="pdf", bbox_inches="tight", dpi=300)
plt.show()
