#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.colors import LogNorm


# Read input image
itk_image = itk.imread("output/box/map_analogu_0_prot_e.nii.gz")
spacing = itk.spacing(itk_image)
# Copy of itk.Image, pixel data is copied
array = itk.array_from_image(itk_image)

# on stocke les dimensions de l'image
x_size = array.shape[3]
y_size = array.shape[2]
z_size = array.shape[1]

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

array_intensity = np.sum(array, axis=0)

# Define the radius and height bins
Max = np.sqrt(x[x_size - 1] ** 2 + z[z_size - 1] ** 2)
R = np.linspace(0, Max, z_size)
H = np.linspace(0, y_size * spacing[2] / 10, y_size)
theta = np.linspace(0, np.pi / 2, 100)  # Angle for cylindrical coordinates
# Initialize the graphs
graph = np.zeros((len(R), len(H)), dtype=float)

# Calculate the bin width
width = spacing[1] / 10
center = int(x_size / 2)  # Center index for the x-axis
dh = spacing[2] / 10
dr = width
for h in range(len(H)):
    Y = h
    for r in range(len(R)):
        for t in range(len(theta)):
            X = int(R[r] * np.cos(theta[t]) / width)
            Z = int(R[r] * np.sin(theta[t]) / width)
            # si hors du cylindre d'intérêt (dans les coins du carré de 14 cm de côté)
            if X >= 100 or Z >= 100:
                continue
            D = R[r] + dr / 2
            quotient = 2 * np.pi * D * dr * dh
            # premier quart
            graph[r, h] += array_intensity[center + Z, Y, center + X] / quotient
            # deuxième quart
            graph[r, h] += array_intensity[center + Z, Y, center - X] / quotient
            # troisième quart
            graph[r, h] += array_intensity[center - Z, Y, center - X] / quotient
            # quatrième quart
            graph[r, h] += array_intensity[center - Z, Y, center + X] / quotient


s, h = np.meshgrid(
    np.linspace(0, 15, x_size),  # r-axis (first dimension in the array)
    H,  # h-axis (second dimension in the array)
    indexing="ij",  # Use 'ij' indexing to match the array's shape
)

s = s.ravel()
h = h.ravel()
values = graph.ravel()
mask = values != 0  # Create a boolean mask for non-zero values
s = s[mask]
h = h[mask]
vmax = 1e-2  # Find the maximum value for normalization
values = values[mask]

fig, ax = plt.subplots(figsize=(8, 6))

# Create a scatter plot for the proton data
p_scatter = ax.scatter(
    s,
    h,  # r and h coordinates
    c=values,  # Color represents the intensity
    marker="o",  # Marker style
    cmap="Reds",
    s=8,
    norm=LogNorm(vmin=1e-7, vmax=vmax),
)  # Normalize color scale

formatter = ScalarFormatter(useMathText=True)  # Create a ScalarFormatter
formatter.set_scientific(True)
formatter.set_powerlimits((-3, 3))  # Set the range for scientific notation

# Add a colorbar
cbar_p = plt.colorbar(p_scatter, ax=ax, shrink=1, pad=0.1)
cbar_p.set_label("cts/protons/mm²")  # Label for the colorbar
# Explicitly set ticks for the colorbar
ticks_p = [1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
cbar_p.set_ticks(ticks_p)
cbar_p.set_ticklabels(
    [f"{tick:.0e}" for tick in ticks_p]
)  # Format ticks as scientific notation

# labels and limits
ax.set_xlabel("radius (cm)")
ax.set_ylabel("depth (cm)")
ax.set_xlim(0, 15)  # R-axis: cm
ax.set_ylim(0, 20)  # H-axis: cm
ax.set_title("2D map of PGs emission by protons", fontsize=16)
plt.grid(True)
plt.savefig("coupe-protons-analog.pdf", bbox_inches="tight")

plt.show()
