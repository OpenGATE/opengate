import numpy as np
import pathlib
import SimpleITK as sitk
import itk
from opengate.geometry.utility import (
    translate_point_to_volume,
    vec_g4_as_np,
)
from opengate.actors.digitizers import *
import sys


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


def add_fake_table_OLD(sim, name="table"):
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


def read_projections_as_sinograms(filenames, nb_of_gantry_angles):
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


def compute_efficiency_from_files(filename, duration):
    img_ref = sitk.ReadImage(str(filename))
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
    vprim, vprim_squared, vscatter, vscatter_squared, n_prim, n_scatter
):

    # means for one event
    if vprim is not None:
        prim = vprim / n_prim
        prim_squared = vprim_squared / n_prim
        prim_var = (prim_squared - np.power(prim, 2)) / (n_prim - 1)
        mean = prim
        variance = prim_var
    if vscatter is not None:
        scatter = vscatter / n_scatter
        scatter_squared = vscatter_squared / n_scatter
        scatter_var = (scatter_squared - np.power(scatter, 2)) / (n_scatter - 1)
        mean = scatter
        variance = scatter_var

    if vprim is not None and vscatter is not None:
        mean = prim + scatter
        variance = prim_var + scatter_var

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
            {"name": "spectrum_full", "min": 3.0, "max": 515.0},
            {"name": "scatter_171_low", "min": 138.4525, "max": 158.4525},
            {"name": "peak_171", "min": 158.4525, "max": 184.1475},
            {"name": "scatter_171_high", "min": 184.1475, "max": 204.1475},
            {"name": "scatter_245_low", "min": 206.995, "max": 226.995},
            {"name": "peak_245", "min": 226.995, "max": 263.805},
            {"name": "scatter_245_high", "min": 263.805, "max": 283.805},
        ]
    if not spectrum_channel:
        channels.pop(0)
    if len(channels) == 0:
        raise ValueError(f"No default energy windows for {radionuclide_name}")
    return channels


def get_mu_from_xraylib(material_symbol, energy):
    """
    Retrieves the linear attenuation coefficient (mu) for a given material and energy.
    Uses the xraylib library to get data from standard physics databases.

    Args:
        material_symbol (str): The chemical symbol of the material (e.g. 'Pb', 'W').
        energy (float): The photon energy (will be used in keV)

    Returns:
        float: The linear attenuation coefficient in cm^-1, or None if the material is unknown.
    """
    try:
        import xraylib
    except ImportError:
        print(
            "Error: The 'xraylib' library is required for dynamic calculations of attenuation coefficients."
        )
        print("Please install it using: pip install xraylib")
        sys.exit(1)

    try:
        # Get atomic number and density for the material from xraylib's database
        atomic_number = xraylib.SymbolToAtomicNumber(material_symbol)
        density = xraylib.ElementDensity(atomic_number)
        # print(f'energy = {energy/ g4_units.keV} keV, material = "{material_symbol}"')

        # Get the total mass attenuation coefficient (cm^2/g).
        # Xraylib expects energy in keV for this function.
        mass_attenuation_coeff = xraylib.CS_Total(atomic_number, energy / g4_units.keV)

        # Calculate linear attenuation coefficient: mu = (mu/rho) * rho
        linear_attenuation_coeff = mass_attenuation_coeff * density

        return linear_attenuation_coeff

    except ValueError:
        print(
            f"Error: Material symbol '{material_symbol}' not found in xraylib database."
        )
        return None


def calculate_acceptance_angle(
    hole_diameter, collimator_length, linear_attenuation_coeff_cm
):
    """
    Calculates the effective length and acceptance angle of a collimator.

    Args:
        hole_diameter (float): The diameter of the collimator hole in mm.
        collimator_length (float): The physical length of the collimator in mm.
        linear_attenuation_coeff_cm (float): The linear attenuation coefficient
                                             of the septal material in cm^-1.

    Returns:
        tuple: A tuple containing (effective_length_mm, acceptance_angle_degrees).
    """

    mm = g4_units.mm

    # Convert mu to mm^-1
    mu_mm = linear_attenuation_coeff_cm / 10.0

    # Calculate effective length: Leff = L - 2/mu
    effective_length_mm = collimator_length / mm - (2 / mu_mm)

    # Calculate acceptance angle: theta = arctan(d / Leff)
    acceptance_angle_rad = np.arctan((hole_diameter / mm) / effective_length_mm)

    # Convert to degrees
    acceptance_angle_degrees = np.rad2deg(acceptance_angle_rad)

    return effective_length_mm, acceptance_angle_degrees


def calculate_max_penetration_angle_OLD(
    septal_thickness_mm, linear_attenuation_coeff_cm, prob_threshold=0.01
):
    """
    Calculates the maximum acceptance angle based on septal penetration
    probability.

    This angle represents the point at which the probability of a photon
    passing through the shortest path in a septum drops to a given threshold.

    Args:
        septal_thickness_mm (float): The thickness of the collimator septa in mm.
        linear_attenuation_coeff_cm (float): The linear attenuation coefficient
                                             of the septal material in cm^-1.
        prob_threshold (float, optional): The transmission probability threshold.
                                          Defaults to 0.01 (1%).

    Returns:
        float: The maximum acceptance angle in degrees.
    """
    # Ensure the probability threshold is valid
    if not 0 < prob_threshold < 1:
        raise ValueError("Probability threshold must be between 0 and 1.")

    # Convert the linear attenuation coefficient from cm^-1 to mm^-1
    mu_mm = linear_attenuation_coeff_cm / 10.0

    # Calculate the argument for arcsin: (-mu * t) / ln(P_th)
    # The numerator is negative, and ln(P_th) is also negative, so the
    # result is positive.
    arcsin_arg = (-mu_mm * septal_thickness_mm) / np.log(prob_threshold)

    # Check if the argument is valid for arcsin (it must be between -1 and 1)
    if arcsin_arg > 1:
        # This can happen if the septa are very thick or mu is very high,
        # making penetration even at 90 degrees less likely than the threshold.
        # In this case, the effective max angle is 90 degrees.
        return 90.0

    # Calculate the angle in radians
    angle_rad = np.arcsin(arcsin_arg)

    # Convert the angle to degrees
    angle_deg = np.rad2deg(angle_rad)

    return angle_deg


def calculate_max_penetration_angle(
    hole_diameter_mm: float,
    collimator_length_mm: float,
    septal_thickness_mm: float,
    linear_attenuation_coeff_cm: float,
    strictness_s: float,
    accurate_cutoff: float = 0.001,
) -> float:
    """
    Calculates the max acceptance angle using a "Strictness" parameter.

    The model interpolates between a purely geometric angle (S=1) and a
    physically accurate angle that includes penetration (S=0).

    Args:
        hole_diameter_mm (float): Diameter of the collimator hole in mm.
        collimator_length_mm (float): Physical length of the collimator in mm.
        septal_thickness_mm (float): Thickness of the collimator septa in mm.
        linear_attenuation_coeff_cm (float): Linear attenuation coefficient
                                             of the septal material in cm^-1.
        strictness_s (float): The strictness parameter, from 0 to 1.
                              S=1 is maximally strict (geometric only).
                              S=0 is minimally strict (fully accurate).
        accurate_cutoff (float, optional): The internal probability cutoff used
                                           to define the 'fully accurate' angle.
                                           Defaults to 0.001 (0.1%).

    Returns:
        float: The maximum acceptance angle in degrees.
    """
    if not 0 <= strictness_s <= 1:
        raise ValueError("Strictness (S) must be between 0 and 1.")

    # --- 1. Calculate the Geometric Angle (S=1 case) ---
    theta_geom = np.rad2deg(np.arctan(hole_diameter_mm / collimator_length_mm))

    # --- 2. Calculate the "Fully Accurate" Angle (S=0 case) ---
    # This is the angle where transmission probability drops to the low cutoff.
    # It represents the widest plausible angle including penetration.
    mu_mm = linear_attenuation_coeff_cm / 10.0
    try:
        # From the physical model: sin(theta) = -mu*t / ln(cutoff)
        arcsin_arg = (-mu_mm * septal_thickness_mm) / np.log(accurate_cutoff)

        if 0 < arcsin_arg < 1:
            theta_accurate = np.rad2deg(np.arcsin(arcsin_arg))
        else:
            # If arg is invalid (e.g., > 1), penetration is essentially
            # impossible. The most accurate model is the geometric one.
            theta_accurate = theta_geom

    except (ValueError, ZeroDivisionError):
        # Handle invalid log() input or other math errors
        theta_accurate = theta_geom

    # --- 3. Interpolate using the Strictness parameter S ---
    # S=1 gives theta_geom, S=0 gives theta_accurate.
    theta_max = strictness_s * theta_geom + (1 - strictness_s) * theta_accurate

    return theta_max


def calculate_theta_max_angle(
    hole_diameter_mm: float,
    collimator_length_mm: float,
    septal_thickness_mm: float,
    linear_attenuation_coeff_cm: float,
) -> float:

    # Calculate the Geometric Angle
    theta_geom = np.rad2deg(np.arctan(hole_diameter_mm / collimator_length_mm))

    # Calculate the effective length, according to mu
    Leff = collimator_length_mm - 2 / linear_attenuation_coeff_cm

    # Calculate the effective angle, according to mu
    theta_acc = np.rad2deg(np.arctan(hole_diameter_mm / Leff))

    # Calculate the crossover max angle
    theta_cross = np.rad2deg(
        np.arctan((hole_diameter_mm + septal_thickness_mm) / collimator_length_mm)
    )

    # print
    print(f"Geometric angle: {theta_geom:.2f} deg")
    print(f"Effective length: {Leff:.2f} mm vs {collimator_length_mm:.2f} mm")
    print(f"Effective angle: {theta_acc:.2f} deg")
    print(f"Crossover angle: {theta_cross:.2f} deg")

    return theta_acc
