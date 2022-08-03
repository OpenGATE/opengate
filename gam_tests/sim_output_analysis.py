import gatetools as gt
import gatetools.phsp as phsp
import itk
import click
import os
import numpy as np
import logging
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
from scipy.optimize import curve_fit


def plot_edep(outputdir, start, end, spacing, fNamePrefix="plane", fNameSuffix="a.mhd"):

    if not os.path.isdir(outputdir):
        os.mkdir(outputdir)  # create directory to save plots

    f = open(outputdir / "sigma_values.txt", "w")
    f.write("Plane_nr sigma_x sigma_y\n")

    f2 = open(outputdir / "mu_values.txt", "w")
    f2.write("Plane_nr mu_x mu_y\n")
    print("fNameSuffix", fNameSuffix)
    print("write mu and sigma file to dir: ")
    print(outputdir)
    for i in range(start, end, spacing):

        filename = fNamePrefix + str(i) + fNameSuffix
        filepath = outputdir / filename

        # Get data from file
        data, spacing, shape = read_mhd(str(filepath))

        # Create color map
        name = "plane_" + str(i) + "_ColorMap.png"
        path = outputdir / name
        # create_color_map(data, path)

        # Line profile in x
        width = shape[2] * spacing[0]
        axis = np.arange(0, width, spacing[0]) - width / 2 + spacing[0] / 2
        dose = np.squeeze(np.sum(data, axis=1))  # integrate dose along y axis
        name = "plane_" + str(i) + "_x_profile.png"
        path = outputdir / name
        parameters = gaussian_fit(axis, dose, path)
        sigma_x = parameters[2]
        mu_x = parameters[1]

        # Line profile in y
        width = shape[1] * spacing[1]
        axis = np.arange(0, width, spacing[1]) - width / 2 + spacing[1] / 2
        dose = np.squeeze(np.sum(data, axis=2))  # integrate dose along z axis
        name = "plane_" + str(i) + "_y_profile.png"
        path = outputdir / name
        parameters = gaussian_fit(axis, dose, path)
        sigma_y = parameters[2]
        mu_y = parameters[1]

        # Write to file
        f.write(str(i) + " " + str(sigma_x) + " " + str(sigma_y) + "\n")
        f2.write(str(i) + " " + str(mu_x) + " " + str(mu_y) + "\n")

    f.close()
    f2.close()


def create_color_map(data, path, show=False):

    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(111)
    ax.set_title("colorMap")
    plt.imshow(data[0, :, :])
    ax.set_aspect("equal")
    plt.colorbar(orientation="vertical")
    if show:
        plt.show()
    else:
        fig.savefig(path)
        plt.close(fig)


def gaussian_fit(axis, dose, path, show=False):

    # Define the Gaussian function for fitting
    def Gauss(x, A, x0, sigma):
        return A * np.exp(-((x - x0) ** 2) / (2 * sigma**2))

    # Fit data with Gaussian func
    mean = sum(axis * dose) / sum(dose)
    sigma = np.sqrt(sum(dose * (axis - mean) ** 2) / sum(dose))
    parameters, covariance = curve_fit(Gauss, axis, dose, p0=[max(dose), mean, sigma])
    fit_y = Gauss(axis, parameters[0], parameters[1], parameters[2])

    # Create figure
    fig, a = plt.subplots()
    a.plot(axis, dose, "o", label="data")
    a.plot(axis, fit_y, "-", label="fit")
    a.set_xlabel("Depth [mm]")
    a.set_ylabel("Dose")
    if show:
        plt.show()
    else:
        fig.savefig(path)
        plt.close(fig)

    return parameters


def compareGaussParam(sigma, ref, rel_tol=0, abs_tol=0, verb=False):

    if rel_tol == 0 and abs_tol == 0:
        print("\033[91m Please provide non-zero tolerance\033[0m")

    with open(sigma, "r") as c1:
        lines1 = np.asarray(c1.readlines()[1:])

    with open(ref, "r") as c2:
        lines_ref = np.asarray(c2.readlines()[1:])

    is_ok = True

    for l, l_r in np.stack((lines1, lines_ref), axis=-1):
        sig_x = float(l.split(" ")[1])
        sig_y = float(l.split(" ")[2])
        plane = float(l.split(" ")[0])

        sig_x_r = float(l_r.split(" ")[1])
        sig_y_r = float(l_r.split(" ")[2])

        diff_x = abs(sig_x - sig_x_r)
        diff_y = abs(sig_y - sig_y_r)

        reldiff_x = (abs(sig_x - sig_x_r) / sig_x_r) * 100
        reldiff_y = (abs(sig_y - sig_y_r) / sig_y_r) * 100

        if verb:
            print(
                "Plane {0}: value x is {1}mm, value x ref is {2}mm ".format(
                    plane, sig_x, sig_x_r
                )
            )
            print(
                "Plane {0}: value y is {1}mm, value y ref is {2}mm ".format(
                    plane, sig_y, sig_y_r
                )
            )

        if diff_x > abs_tol and reldiff_x > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along x is {1}%, threshold is {2}% \033[0m".format(
                    plane, reldiff_x, rel_tol
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along x is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, diff_x, abs_tol
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along x is ok")

        if diff_y > abs_tol and reldiff_y > rel_tol:
            print(
                "\033[91m Plane {0}:  rel difference along y is {1}%, threshold is {2}% \033[0m".format(
                    plane, reldiff_y, rel_tol
                )
            )
            print(
                "\033[91m Plane {0}:  abs difference along y is {1}mm, threshold is {2}mm \033[0m".format(
                    plane, diff_y, abs_tol
                )
            )
            is_ok = False
        else:
            print("Plane " + str(plane) + " along y is ok")

    if is_ok:
        print("differences below threshold")
    else:
        print("\033[91m differences NOT OK \033[0m")

    return is_ok


def read_mhd(filename):

    img = itk.imread(filename)
    data = itk.GetArrayViewFromImage(img)
    spacing = img.GetSpacing()
    shape = data.shape
    return data, spacing, shape
