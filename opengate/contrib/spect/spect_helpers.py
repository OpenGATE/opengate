import numpy as np
import pathlib
import SimpleITK as sitk
import itk
from pathlib import Path
from opengate.geometry.utility import (
    translate_point_to_volume,
    vec_g4_as_np,
)
from opengate.actors.digitizers import *


def add_fake_table(sim, name="table"):
    """
    Add a patient table (fake)
    """

    # unit
    mm = g4_units.mm
    cm = g4_units.cm
    cm3 = g4_units.cm3
    deg = g4_units.deg
    gcm3 = g4_units.g / cm3

    # colors
    red = [1, 0.7, 0.7, 0.8]
    white = [1, 1, 1, 1]

    sim.volume_manager.material_database.add_material_weights(
        f"CarbonFiber", ["C"], [1], 1.78 * gcm3
    )

    # main bed
    table = sim.add_volume("Tubs", f"{name}_table")
    table.mother = "world"
    table.rmax = 439 * mm
    table.rmin = 406 * mm
    table.dz = 200 * cm / 2.0
    table.sphi = 0 * deg
    table.dphi = 70 * deg
    table.translation = [0, 25 * cm, 0]
    table.rotation = Rotation.from_euler("z", -125, degrees=True).as_matrix()
    table.material = "CarbonFiber"
    table.color = white

    # interior of the table
    tablein = sim.add_volume("Tubs", f"{name}_tablein")
    tablein.mother = table.name
    tablein.rmax = 436.5 * mm
    tablein.rmin = 408.5 * mm
    tablein.dz = 200 * cm / 2.0
    tablein.sphi = 0 * deg
    tablein.dphi = 69 * deg
    tablein.translation = [0, 0, 0]
    tablein.rotation = Rotation.from_euler("z", 0.5, degrees=True).as_matrix()
    tablein.material = "G4_AIR"
    tablein.color = red

    return table


def get_volume_position_in_head(sim, spect_name, vol_name, pos="max", axis=2):
    vol = sim.volume_manager.volumes[f"{spect_name}_{vol_name}"]
    pMin, pMax = vol.bounding_limits
    x = pMax
    if pos == "min":
        x = pMin
    if pos == "center":
        x = pMin + (pMax - pMin) / 2.0
    x = vec_g4_as_np(x)
    x = translate_point_to_volume(sim, vol, spect_name, x)
    return x[axis]


def extract_energy_window_itk(
    image: itk.Image,
    energy_window: int = "all",
    nb_of_energy_windows: int = 3,
    nb_of_gantries: int = 60,
) -> itk.Image:
    """
    Extracts a given energy window from a 3D image and returns a reshaped image.

    3rd dim is number_of_energy_window x number_of_gantries

    Args:
        image (itk.Image): The input 3D image of shape (e.g. 128 x 128 x 3 x 60).
        energy_window : which energy windows to extract (int or 'all').
        nb_of_energy_windows (int): the number of energy windows
        nb_of_gantries (int): The number of gantry positions (default: 60).

    Returns:
        itk.Image: The extracted and reshaped image of shape (128 x 128 x 60).
    """

    # Validate input dimensions
    width, height, depth = image.GetSize()
    if depth != nb_of_gantries * nb_of_energy_windows:
        raise ValueError(
            f"Input image depth {depth} does not match expected "
            f"dimensions = {nb_of_gantries} x {nb_of_energy_windows}."
        )

    # Extract the relevant slices
    # (warning numpy is z,x,y, while itk is x,y,z)
    arr = itk.GetArrayViewFromImage(image)
    sub_image_array = arr[energy_window::nb_of_energy_windows, :, :]

    # Convert the numpy array back to a SimpleITK image
    sub_image = itk.GetImageFromArray(sub_image_array)

    # Preserve the original image metadata
    sub_image.SetSpacing(image.GetSpacing())
    sub_image.SetOrigin(image.GetOrigin())
    sub_image.SetDirection(image.GetDirection())

    return sub_image


def extract_energy_window_from_projection_actors(
    projections,
    energy_window: int = "all",
    nb_of_energy_windows: int = 3,
    nb_of_gantries: int = 60,
    output_filenames=None,
):
    auto_output_filenames = output_filenames is None
    if auto_output_filenames:
        output_filenames = []
    i = 0
    for proj in projections:
        filename = proj.get_output_path()
        img = itk.imread(filename)
        out = extract_energy_window_itk(
            img,
            energy_window=energy_window,
            nb_of_energy_windows=nb_of_energy_windows,
            nb_of_gantries=nb_of_gantries,
        )
        if auto_output_filenames:
            extension = pathlib.Path(filename).suffix
            output_filename = str(filename).replace(
                extension, f"_ene_{energy_window}{extension}"
            )
            output_filenames.append(output_filename)
        else:
            output_filename = output_filenames[i]
        itk.imwrite(out, output_filename)
        i += 1
    return output_filenames


def merge_several_heads_projections(filenames):
    output_arr = None
    img = None
    for filename in filenames:
        img = itk.imread(filename)
        arr = itk.GetArrayFromImage(img)
        if output_arr is None:
            output_arr = arr
        else:
            output_arr = np.concatenate((output_arr, arr), axis=0)

    output_img = itk.GetImageFromArray(output_arr)
    output_img.CopyInformation(img)
    return output_img


def read_projections_as_sinograms(
    projections_folder, projections_filenames, nb_of_gantry_angles
):
    """
    Reads projection files from a specified folder, processes them into sinograms per
    energy window, and ensures consistency in image metadata across all projections.

    Args:
        projections_folder (str|Path): Path to the folder containing projection files.
        projections_filenames : List of projection filenames to read.
        nb_of_gantry_angles (int): Number of gantry angles in the projections.

    Returns:
        list[sitk.Image]: List of SimpleITK Image objects containing the sinograms per
        energy window.
    """
    # get all filenames
    filenames = [Path(projections_folder) / f for f in projections_filenames]

    # init variables
    sinograms_per_energy_window = None
    nb_of_energy_windows = None
    projection_size = None
    projection_origin = None
    projection_spacing = None

    # read all projection files (one per head)
    for f in filenames:
        img = sitk.ReadImage(f)

        if nb_of_energy_windows is None:
            nb_of_energy_windows = int(img.GetSize()[2] / nb_of_gantry_angles)
            projection_size = img.GetSize()
            projection_origin = img.GetOrigin()
            projection_spacing = img.GetSpacing()
            sinograms_per_energy_window = [None] * nb_of_energy_windows

        # check that size and origin are the same for all images
        if img.GetSize() != projection_size:
            raise ValueError(
                f"Projections in {f} have different size than in {filenames[0]}"
            )
        if img.GetOrigin() != projection_origin:
            raise ValueError(
                f"Projections in {f} have different origin than in {filenames[0]}"
            )
        if img.GetSpacing() != projection_spacing:
            raise ValueError(
                f"Projections in {f} have different spacing than in {filenames[0]}"
            )

        # convert to numpy array
        arr = sitk.GetArrayViewFromImage(img)

        # concatenate projections for the different heads, for each energy windows
        for ene in range(nb_of_energy_windows):
            # this is important to make a copy here !
            # Otherwise, the concatenate operation may fail later
            a = arr[ene::nb_of_energy_windows, :, :].copy()
            if sinograms_per_energy_window[ene] is None:
                sinograms_per_energy_window[ene] = a
            else:
                sinograms_per_energy_window[ene] = np.concatenate(
                    (sinograms_per_energy_window[ene], a), axis=0
                )

    # build sitk image from np arrays (to keep spacing, origin information)
    sinograms = []
    for ene in range(nb_of_energy_windows):
        img = sitk.GetImageFromArray(sinograms_per_energy_window[ene])
        img.SetSpacing(projection_spacing)
        img.SetOrigin(projection_origin)
        img.SetDirection(img.GetDirection())
        sinograms.append(img)
    return sinograms


def poisson_rel_uncertainty(np_image):
    """
    Uncertainty for Poisson counts is sqrt(counts) = standard deviation
    Relative uncertainty is sqrt(counts)/counts
    """
    relative_uncertainty = np_image
    uncertainty = np.sqrt(np_image)
    relative_uncertainty = np.divide(
        uncertainty,
        relative_uncertainty,
        out=np.zeros_like(relative_uncertainty),
        where=relative_uncertainty != 0,
    )
    return relative_uncertainty


def poisson_rel_uncertainty_from_files(input_filename, output_rel_uncert=None):
    """ """
    img = sitk.ReadImage(input_filename)
    relative_uncertainty = sitk.GetArrayFromImage(img)
    relative_uncertainty = poisson_rel_uncertainty(relative_uncertainty)
    if output_rel_uncert is not None:
        uncert = sitk.GetImageFromArray(relative_uncertainty)
        uncert.CopyInformation(img)
        sitk.WriteImage(uncert, output_rel_uncert)
    return relative_uncertainty


def batch_rel_uncertainty(np_images):
    """
    Computes the mean and the relative uncertainty of the given images as np arrays.
    Parameters:
        np_images (list of np.ndarray): List of Numpy arrays from images.
    Returns:
        np.ndarray: The mean image.
        np.ndarray: The relative uncertainty image.
    """
    mean = None
    nb_batch = len(np_images)

    # Compute mean
    for m in np_images:
        if mean is None:
            mean = m.copy()
        else:
            mean += m
    mean /= nb_batch

    # Compute standard deviation (variance)
    squared = None
    for m in np_images:
        diff_squared = np.power(m - mean, 2)
        if squared is None:
            squared = diff_squared
        else:
            squared += diff_squared

    # Compute uncertainty
    uncert = np.sqrt(np.divide(squared, nb_batch * (nb_batch - 1)))

    # Compute relative uncertainty in %
    uncert = np.divide(uncert, mean, out=np.zeros_like(mean), where=mean != 0)

    return mean, uncert


def batch_rel_uncertainty_from_files(
    image_filenames, mean_filename=None, rel_uncert_filename=None
):
    """
    Wrapper function that reads images from file, computes relative uncertainty, and writes results to files.
    Parameters:
        image_filenames (list of str): List of image file paths.
        mean_filename (str): Path to save the mean image (optional).
        rel_uncert_filename (str): Path to save the relative uncertainty image (optional).
    Returns:
        np.ndarray: The mean image.
        np.ndarray: The relative uncertainty image.
    """
    # Read images into Numpy arrays
    np_images = [sitk.GetArrayFromImage(sitk.ReadImage(f)) for f in image_filenames]

    # Compute mean and relative uncertainty
    mean, uncert = batch_rel_uncertainty(np_images)

    # Write results back to files if filenames are provided
    if mean_filename is not None:
        img = sitk.GetImageFromArray(mean)
        img.CopyInformation(sitk.ReadImage(image_filenames[0]))
        sitk.WriteImage(img, str(mean_filename))
    if rel_uncert_filename is not None:
        img = sitk.GetImageFromArray(uncert)
        img.CopyInformation(sitk.ReadImage(image_filenames[0]))
        sitk.WriteImage(img, str(rel_uncert_filename))

    return mean, uncert


def compute_efficiency(np_uncert, duration):
    ones = np.ones_like(np_uncert)
    eff = np.divide(
        ones,
        np.power(np_uncert, 2) * duration,
        out=np.zeros_like(np_uncert),
        where=np_uncert != 0,
    )
    return eff


def history_rel_uncertainty(np_img, np_img_squared, n):
    mean = np_img / n
    squared = np_img_squared / n
    variance = (squared - np.power(mean, 2)) / (n - 1)
    uncertainty = np.divide(
        np.sqrt(variance),
        mean,
        out=np.zeros_like(variance),
        where=mean != 0,
    )
    return uncertainty


def history_rel_uncertainty_from_files(
    img_filename,
    img_squared_filename,
    n,
    output_filename=None,
):
    # primary
    img = sitk.ReadImage(img_filename)
    img_squared = sitk.ReadImage(img_squared_filename)
    mean = sitk.GetArrayFromImage(img)
    squared = sitk.GetArrayFromImage(img_squared)

    # compute
    uncert = history_rel_uncertainty(mean, squared, n)

    if output_filename is not None:
        img_uncert = sitk.GetImageFromArray(uncert)
        img_uncert.CopyInformation(img)
        sitk.WriteImage(img_uncert, output_filename)

    return uncert, mean, squared


def history_ff_combined_rel_uncertainty(
    prim_mean, prim_squared, scatter_mean, scatter_squared, n_prim, n_scatter
):
    # means
    prim_mean = prim_mean / n_prim
    prim_squared = prim_squared / n_prim
    scatter_mean = scatter_mean / n_scatter
    scatter_squared = scatter_squared / n_scatter

    # variances
    prim_var = (prim_squared - np.power(prim_mean, 2)) / (n_prim - 1)
    scatter_var = (scatter_squared - np.power(scatter_mean, 2)) / (n_scatter - 1)

    # combine uncertainty
    r = n_prim / n_scatter
    mean = prim_mean + scatter_mean * r
    variance = prim_var + scatter_var * np.power(r, 2)
    uncert = np.divide(
        np.sqrt(variance),
        mean,
        out=np.zeros_like(variance),
        where=mean != 0,
    )

    # rescale the mean for the final results
    mean = mean * n_prim

    return uncert, mean


def batch_ff_combined_rel_uncertainty(
    prim_mean, prim_uncert, scatter_mean, scatter_uncert, n_prim, n_scatter
):
    # combine mean
    r = n_prim / n_scatter
    mean = prim_mean + scatter_mean * r

    # combine uncertainties
    prim_var = np.power(prim_uncert * prim_mean, 2)
    sc_var = np.power(scatter_uncert * scatter_mean, 2) * np.power(r, 2)
    uncert = np.sqrt(prim_var + sc_var)
    uncert = np.divide(
        uncert,
        mean,
        out=np.zeros_like(uncert),
        where=mean != 0,
    )

    return uncert, mean
