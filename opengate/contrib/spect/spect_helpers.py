import numpy as np
import pathlib
import SimpleITK as sitk
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
    table.translation = [0, -25 * cm, 0]
    table.rotation = Rotation.from_euler("z", 55, degrees=True).as_matrix()
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


def get_volume_bounding_box_coordinate_in_frame(
    sim, spect_name, vol_name, pos="max", axis=2
):
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


def extract_energy_window_from_projections(
    image,
    energy_window="all",
    nb_of_energy_windows=3,
    nb_of_gantries=60,
):
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
    arr = sitk.GetArrayViewFromImage(image)
    sub_image_array = arr[energy_window::nb_of_energy_windows, :, :]

    # Convert the numpy array back to a SimpleITK image
    sub_image = sitk.GetImageFromArray(sub_image_array)

    # Preserve the original image metadata
    sub_image.SetSpacing(image.GetSpacing())
    sub_image.SetOrigin(image.GetOrigin())
    sub_image.SetDirection(image.GetDirection())

    return sub_image


def extract_energy_window_from_actor_files(
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
        img = sitk.ReadImage(filename)
        out = extract_energy_window_from_projections(
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
        sitk.WriteImage(out, output_filename)
        i += 1
    return output_filenames


def load_and_merge_multi_head_projections(filenames, nb_of_gantry_angles):
    """
    Reads projection files from a specified folder, processes them into sinograms per
    energy window, and ensures consistency in image metadata across all projections.

    Args:
        filenames : List of projection filenames to read.
        nb_of_gantry_angles (int): Number of gantry angles in the projections.

    Returns:
        list[sitk.Image]: List of SimpleITK Image objects containing the sinograms per
        energy window.
    """
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

        if nb_of_energy_windows < 1:
            raise ValueError(
                f"nb_of_energy_windows={nb_of_energy_windows} is invalid ; "
                f"image size is {img.GetSize()} and "
                f"nb of angles is {nb_of_gantry_angles}"
            )

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

        # convert to a numpy array
        arr = sitk.GetArrayViewFromImage(img)

        # concatenate projections for the different heads and for each energy window
        for ene in range(nb_of_energy_windows):
            # this is important to make a copy here!
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


def get_default_energy_windows(radionuclide_name, spectrum_channel=False):
    n = radionuclide_name.lower()
    keV = g4_units.keV
    channels = []

    if "177lu" in n or "lu177" in n:
        channels = [
            {"name": f"spectrum", "min": 3 * keV, "max": 515 * keV},
            {"name": f"scatter1", "min": 84.75 * keV, "max": 101.7 * keV},
            {"name": f"peak113", "min": 101.7 * keV, "max": 124.3 * keV},
            {"name": f"scatter2", "min": 124.3 * keV, "max": 141.25 * keV},
            {"name": f"scatter3", "min": 145.6 * keV, "max": 187.2 * keV},
            {"name": f"peak208", "min": 187.2 * keV, "max": 228.8 * keV},
            {"name": f"scatter4", "min": 228.8 * keV, "max": 270.4 * keV},
        ]

    if "tc99m" in n:
        channels = [
            {"name": f"spectrum", "min": 3 * keV, "max": 160 * keV},
            {"name": f"scatter", "min": 108.58 * keV, "max": 129.59 * keV},
            {"name": f"peak140", "min": 129.59 * keV, "max": 150.61 * keV},
        ]

    if "in111" in n or "111in" in n:
        # 15% around the peaks
        channels = [
            {"name": "spectrum_full", "min": 3.0 * keV, "max": 515.0 * keV},
            {"name": "scatter_171_low", "min": 138.4525 * keV, "max": 158.4525 * keV},
            {"name": "peak_171", "min": 158.4525 * keV, "max": 184.1475 * keV},
            {"name": "scatter_171_high", "min": 184.1475 * keV, "max": 204.1475 * keV},
            {"name": "scatter_245_low", "min": 206.995 * keV, "max": 226.995 * keV},
            {"name": "peak_245", "min": 226.995 * keV, "max": 263.805 * keV},
            {"name": "scatter_245_high", "min": 263.805 * keV, "max": 283.805 * keV},
        ]

    if "i123" in n or "123i" in n:
        # 20% window around 159 keV peak
        channels = [
            {"name": "spectrum", "min": 3 * keV, "max": 200 * keV},
            {"name": "scatter_low", "min": 125 * keV, "max": 143.1 * keV},
            {"name": "peak159", "min": 143.1 * keV, "max": 174.9 * keV},
            {"name": "scatter_high", "min": 174.9 * keV, "max": 195 * keV},
        ]

    if "i131" in n or "131i" in n:
        # 20% window around 364 keV peak
        channels = [
            {"name": "spectrum", "min": 3 * keV, "max": 410 * keV},
            {"name": "scatter_low", "min": 285 * keV, "max": 327.6 * keV},
            {"name": "peak364", "min": 327.6 * keV, "max": 400.4 * keV},
        ]

    if not spectrum_channel:
        channels.pop(0)
    if len(channels) == 0:
        raise ValueError(f"No default energy windows for {radionuclide_name}")
    return channels


def compute_poisson_relative_uncertainty(np_image):
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


def compute_poisson_relative_uncertainty_from_file(
    input_filename, output_rel_uncert=None
):
    """ """
    img = sitk.ReadImage(input_filename)
    relative_uncertainty = sitk.GetArrayFromImage(img)
    relative_uncertainty = compute_poisson_relative_uncertainty(relative_uncertainty)
    if output_rel_uncert is not None:
        uncert = sitk.GetImageFromArray(relative_uncertainty)
        uncert.CopyInformation(img)
        sitk.WriteImage(uncert, output_rel_uncert)
    return relative_uncertainty


def compute_batch_mean_and_relative_uncertainty(np_images):
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


def compute_batch_mean_and_relative_uncertainty_from_files(
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
    mean, uncert = compute_batch_mean_and_relative_uncertainty(np_images)

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


def compute_efficiency_from_files(uncert_filename, duration):
    img_ref = sitk.ReadImage(str(uncert_filename))
    np_uncert = sitk.GetArrayFromImage(img_ref)
    return compute_efficiency(np_uncert, duration)


def compute_efficiency(np_uncert, duration):
    ones = np.ones_like(np_uncert)
    eff = np.divide(
        ones,
        (np_uncert * np_uncert) * duration,
        out=np.zeros_like(np_uncert),
        where=np_uncert != 0,
    )
    return eff


def compute_history_by_history_relative_uncertainty(np_img, np_img_squared, n):
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


def compute_history_by_history_relative_uncertainty_from_files(
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
    uncert = compute_history_by_history_relative_uncertainty(mean, squared, n)

    if output_filename is not None:
        img_uncert = sitk.GetImageFromArray(uncert)
        img_uncert.CopyInformation(img)
        sitk.WriteImage(img_uncert, output_filename)

    return uncert, mean, squared


def compute_zscore(ref_counts_np, test_counts_np, var_ref, var_test):
    not_zero = (ref_counts_np != 0) & (test_counts_np != 0)
    z_score = np.divide(
        test_counts_np - ref_counts_np,
        np.sqrt(var_ref + var_test),
        out=np.zeros_like(ref_counts_np),
        where=not_zero,
    )
    z_score = z_score.astype(np.float64)
    return z_score


def compute_zscore_from_files(
    ref_filename,
    test_filename,
    ref_uncert_filename,
    test_uncert_filename,
    output_filename=None,
):
    # read data
    img = sitk.ReadImage(ref_filename)
    ref_counts_np = sitk.GetArrayFromImage(img)
    test_counts_np = sitk.GetArrayFromImage(sitk.ReadImage(test_filename))
    ref_uncert = sitk.GetArrayFromImage(sitk.ReadImage(ref_uncert_filename))
    test_uncert = sitk.GetArrayFromImage(sitk.ReadImage(test_uncert_filename))

    # compute var and zscore
    var_ref = (ref_uncert * ref_counts_np) ** 2
    var_test = (test_uncert * test_counts_np) ** 2
    z_score = compute_zscore(ref_counts_np, test_counts_np, var_ref, var_test)

    # write results
    if output_filename is not None:
        img = sitk.GetImageFromArray(z_score)
        img.CopyInformation(img)
        sitk.WriteImage(img, output_filename)

    return z_score


def compute_zscore_from_folders(
    ref_folder,
    test_folder,
    counts_filename="projection_0_counts.mhd",
    uncert_filename="relative_uncertainty_0_counts.mhd",
):
    return compute_zscore_from_files(
        ref_folder / counts_filename,
        test_folder / counts_filename,
        ref_folder / uncert_filename,
        test_folder / uncert_filename,
        output_filename=test_folder / "zscore.mhd",
    )


def compute_speedup(
    ref_uncert, test_uncert, ref_duration, test_duration, output_filename=None
):
    ref_eff = compute_efficiency(ref_uncert, ref_duration)
    test_eff = compute_efficiency(test_uncert, test_duration)
    speedup = np.divide(
        test_eff, ref_eff, out=np.zeros_like(test_eff), where=ref_eff != 0
    )
    speedup = speedup.astype(np.float64)
    return speedup


def compute_speedup_from_files(
    ref_uncert_filename,
    test_uncert_filename,
    ref_duration,
    test_duration,
    output_filename=None,
):
    img = sitk.ReadImage(ref_uncert_filename)
    ref_uncert = sitk.GetArrayFromImage(img)
    test_uncert = sitk.GetArrayFromImage(sitk.ReadImage(test_uncert_filename))
    speedup = compute_speedup(ref_uncert, test_uncert, ref_duration, test_duration)
    if output_filename is not None:
        img_speedup = sitk.GetImageFromArray(speedup)
        img_speedup.CopyInformation(img)
        sitk.WriteImage(img_speedup, output_filename)
    return speedup


def compute_speedup_from_folders(
    ref_folder,
    test_folder,
    ref_duration,
    test_duration,
    uncert_filename="relative_uncertainty_0_counts.mhd",
):
    return compute_speedup_from_files(
        ref_folder / uncert_filename,
        test_folder / uncert_filename,
        ref_duration,
        test_duration,
        output_filename=test_folder / "speedup.mhd",
    )
