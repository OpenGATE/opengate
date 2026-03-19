# if pytomography is not installed, we ignore this module
# this is needed for test080_check_classes_are_processed.py
# that check all modules
try:
    import pytomography
except ModuleNotFoundError:
    print("pytomography module is not installed. Skipping pytomography_helpers.")
    import sys

    # Unload this module to prevent errors in other imports
    sys.modules[__name__] = None
    raise SystemExit

from opengate.exception import warning
from opengate.contrib.spect.spect_config import *
from opengate.image import resample_itk_image
from opengate.contrib.dose.photon_attenuation_image_helpers import (
    create_photon_attenuation_image,
)
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta, SPECTPSFMeta
from pytomography.transforms.SPECT import SPECTPSFTransform, SPECTAttenuationTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM
from pytomography.utils import compute_EW_scatter
import torch
import SimpleITK as sitk
import itk
import numpy as np
import json
from pathlib import Path
import warnings


def convert_image_gate_to_pytomo(np_image):
    """
    Convert a numpy image to the pytomography coordinate system.
    => works in both direction (convert_image_pytomo_to_gate)
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    rotation_arr = rotation_arr[:, ::-1, :].copy()
    return rotation_arr


def convert_image_pytomo_to_gate(np_image):
    """
    Convert a pytomography numpy image to the gate coordinate system.
    => works in both direction (convert_image_gate_to_pytomo)
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    rotation_arr = rotation_arr[:, ::-1, :].copy()
    return rotation_arr


def convert_sinogram_gate_to_pytomo(np_sinogram):
    """
    Rotate numpy sinogram to the Pytomography coordinate system [angles,z,x] -> [angles,x,z]
    we reverse the Z axis (gantry rotation) because the rotation of the
    gantry is in the opposite direction
    """
    rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
    rotated_sinogram = rotated_sinogram[:, :, ::-1].copy()
    return rotated_sinogram


def pytomography_read_metadata(json_file):
    json_file = Path(json_file).resolve()
    with open(json_file, "r") as f:
        metadata = json.load(f)
        metadata["folder"] = json_file.parent
    return metadata


def pytomography_new_metadata():
    return {
        "Energy Window Data": {
            "energy_window_lower_bounds": [],
            "energy_window_upper_bounds": [],
            "number_of_energy_windows": 0,
        },
        "Detector Physics Data": {
            # some default values as an example
            "hole_shape": 6,
            "hole_diameter": 0.294,
            "hole_spacing": 0.4,
            "collimator_thickness": 4.064,
            "collimator_material": "lead",
            "crystal_spatial_resolution_fwhm_energy_model": "A*sqrt(B/energy)",
            "crystal_spatial_resolution_fwhm_energy_model_parameters": [0.36, 140.5],
            "crystal_energy_resolution_fwhm_pct_energy_model": "A*sqrt(B/energy)",
            "crystal_energy_resolution_fwhm_pct_energy_model_parameters": [9.9, 140.5],
            "crystal_width": 55.3,
            "crystal_height": 38.1,
            "isotope_name": "Lu177",
        },
        "Attenuation Data": {
            "source_file": None,
            "voxel_size_x": 0.24,
            "voxel_size_y": 0.24,
            "voxel_size_z": 0.24,
            "dimension_x": 256,
            "dimension_y": 256,
            "dimension_z": 256,
            "origin_x": -30.599999999999998,
            "origin_y": -30.599999999999998,
            "origin_z": -30.599999999999998,
            "energy": 208,
        },
        "Projection Geometry Data": {
            "source_file": None,
            "number_of_projections": 0,
            "detector_position_x": [],
            "detector_position_y": [],
            "detector_position_z": [],
            "detector_orientation_x": [],
            "detector_orientation_y": [],
            "detector_orientation_z": [],
            "projection_pixel_size_r": 0.48,
            "projection_pixel_size_z": 0.48,
            "projection_dimension_r": 128,
            "projection_dimension_z": 128,
            "starting_angle_deg": -90,
        },
    }


def pytomography_add_detector_orientation(metadata, detector):
    geom = metadata["Projection Geometry Data"]
    for dp in detector.dynamic_params.values():
        translations = np.array(dp["translation"]) / g4_units.cm
        rotations = dp["rotation"]
        for tr, rot in zip(translations, rotations):
            # translation and rotation are according to the mother volume of the detector
            geom["detector_position_x"].append(tr[0])
            geom["detector_position_y"].append(tr[1])
            # detector_orientation_z is *not* used yet by pytomography
            geom["detector_position_z"].append(tr[2])
            # detector_orientation is *not* used yet by pytomography
            geom["detector_orientation_x"].append(rot[0].tolist())
            geom["detector_orientation_y"].append(rot[1].tolist())
            geom["detector_orientation_z"].append(rot[2].tolist())
        geom["number_of_projections"] += len(translations)


def pytomography_set_detector_info(metadata, pixel_spacing, dimension):
    geom = metadata["Projection Geometry Data"]
    geom["projection_pixel_size_r"] = pixel_spacing[0] / g4_units.cm
    geom["projection_pixel_size_z"] = pixel_spacing[1] / g4_units.cm
    geom["projection_dimension_r"] = dimension[0]
    geom["projection_dimension_z"] = dimension[1]


def pytomography_set_energy_windows(metadata, channels):
    ew = metadata["Energy Window Data"]
    for channel in channels:
        ew["energy_window_lower_bounds"].append(channel["min"])
        ew["energy_window_upper_bounds"].append(channel["max"])
        ew["number_of_energy_windows"] += 1


# FIXME => SHOULD BE REMOVED ; replace with GateToPyTomographyAdapter system
def pytomography_create_sinogram(filenames, number_of_angles, output_filename):
    # consider sinogram for all energy windows
    sinograms = load_and_merge_multi_head_projections(filenames, number_of_angles)
    sino_arr = None
    for sinogram in sinograms:
        arr = sitk.GetArrayFromImage(sinogram)
        arr = convert_sinogram_gate_to_pytomo(arr)
        # concatenate all energy windows
        if sino_arr is None:
            sino_arr = arr
        else:
            sino_arr = np.concatenate((sino_arr, arr), axis=0)

    sino_itk = sitk.GetImageFromArray(sino_arr)
    sino_itk.SetSpacing(sinograms[0].GetSpacing())
    sino_itk.SetOrigin(sinograms[0].GetOrigin())
    sino_itk.SetDirection(sinograms[0].GetDirection())
    sitk.WriteImage(sino_itk, output_filename)
    return sino_arr


def create_attenuation_image(
    ct_filename,
    energy,
    attenuation_filename,
    size,
    spacing,
    translation=None,
    verbose=False,
):
    # resample
    image = itk.imread(ct_filename)
    verbose and print(f"Resample CT image {ct_filename} to {size} and {spacing}")
    image = resample_itk_image(
        image,
        size,
        spacing,
        default_pixel_value=-1000,
        linear=False,
        translation=translation,
    )
    itk.imwrite(image, attenuation_filename)

    # mumap
    verbose and print(f"Compute attenuation map for E={energy / g4_units.MeV} MeV")
    attenuation_image = create_photon_attenuation_image(
        attenuation_filename,
        labels_filename=None,
        energy=energy,
        material_database=None,
        database="EPDL",
        verbose=False,
        density_tol=0.05 * gate.g4_units.g_cm3,
    )
    itk.imwrite(attenuation_image, attenuation_filename)


def pytomography_set_attenuation_data(
    metadata,
    energy,
    attenuation_filename,
    translation=None,
    verbose=False,
):
    # check attenuation_filename must be mhd/raw
    attenuation_filename = Path(attenuation_filename)
    # if attenuation_filename.suffix != ".mhd":
    #    fatal(
    #        f"Attenuation file must be mhd/raw, while the "
    #        f"extension is {attenuation_filename.suffix} ({attenuation_filename})"
    #    )
    raw_filename = attenuation_filename  # .with_suffix(".raw")

    # read attenuation image
    attenuation_image = sitk.ReadImage(attenuation_filename)
    size = attenuation_image.GetSize()
    spacing = attenuation_image.GetSpacing()

    # information and translation
    if translation is None:
        translation = np.array([0, 0, 0])
    else:
        translation = np.array(translation)
    verbose and print(f"Phantom translation: {translation}")
    ad = metadata["Attenuation Data"]
    ad["source_file"] = str(raw_filename.name)
    ad["energy"] = energy / g4_units.keV  # this is not used by pytomography
    ad["voxel_size_x"] = spacing[0] / g4_units.cm
    ad["voxel_size_y"] = spacing[1] / g4_units.cm
    ad["voxel_size_z"] = spacing[2] / g4_units.cm
    ad["dimension_x"] = size[0]
    ad["dimension_y"] = size[1]
    ad["dimension_z"] = size[2]
    ad["origin_x"] = attenuation_image.GetOrigin()[0] / g4_units.cm
    ad["origin_y"] = attenuation_image.GetOrigin()[1] / g4_units.cm
    ad["origin_z"] = attenuation_image.GetOrigin()[2] / g4_units.cm
    ad["translation"] = (translation / g4_units.cm).tolist()


# ------ below should be in pytomography ? --------


def pytomography_get_detector_data(metadata):
    geometry_meta = metadata["Projection Geometry Data"]
    detector_position_x = np.array(geometry_meta["detector_position_x"])
    detector_position_y = np.array(geometry_meta["detector_position_y"])

    # the following are not used yet
    detector_position_z = np.array(geometry_meta["detector_position_z"])
    detector_orientation_x = np.array(geometry_meta["detector_orientation_x"])
    detector_orientation_y = np.array(geometry_meta["detector_orientation_y"])
    detector_orientation_z = np.array(geometry_meta["detector_orientation_z"])

    # pixel size and spacing
    projection_pixel_size_r = geometry_meta["projection_pixel_size_r"]
    projection_pixel_size_z = geometry_meta["projection_pixel_size_z"]
    projection_dimension_r = geometry_meta["projection_dimension_r"]
    projection_dimension_z = geometry_meta["projection_dimension_z"]

    # For now, assume all oriented towards the centre
    radii = np.sqrt(detector_position_x**2 + detector_position_y**2)
    angles = np.arctan2(detector_position_y, detector_position_x)

    # starting angle
    angles = np.degrees(angles) + geometry_meta["starting_angle_deg"]

    object_meta = SPECTObjectMeta(
        [projection_pixel_size_r, projection_pixel_size_r, projection_pixel_size_z],
        [projection_dimension_r, projection_dimension_r, projection_dimension_z],
    )

    proj_meta = SPECTProjMeta(
        [projection_dimension_r, projection_dimension_z],
        [projection_pixel_size_r, projection_pixel_size_z],
        angles,
        radii,
    )

    return object_meta, proj_meta


def pytomography_read_projections(metadata, folder=None):
    object_meta, proj_meta = pytomography_get_detector_data(metadata)
    energy_meta = metadata["Energy Window Data"]
    number_of_energy_windows = energy_meta["number_of_energy_windows"]
    geometry_meta = metadata["Projection Geometry Data"]
    image_file = geometry_meta["source_file"]
    if folder is None:
        folder = Path(metadata["folder"])
    projections_img = sitk.ReadImage(str(folder / image_file))
    projections = sitk.GetArrayFromImage(projections_img).astype(np.float32)
    projections = projections.reshape(number_of_energy_windows, *proj_meta.shape)
    projections = torch.tensor(projections).to(pytomography.device)
    return projections


def create_physics_psf_2param(hole_diameter_mm, hole_length_mm, intrinsic_fwhm_mm):
    # 1. Force everything to PyTomography's native unit: Centimeters
    hole_diam_cm = hole_diameter_mm / 10.0
    hole_len_cm = hole_length_mm / 10.0
    int_fwhm_cm = intrinsic_fwhm_mm / 10.0

    FWHM2sigma = 1.0 / 2.355

    # 2. Slope 'sigma_a' (dimensionless)
    # The rate at which the cone expands over distance
    sigma_a = (hole_diam_cm / hole_len_cm) * FWHM2sigma

    # 3. Intercept 'sigma_b' (in cm)
    # We combine the hole size and intrinsic blur into a single baseline blur at d=0
    fwhm_at_face_cm = np.sqrt(hole_diam_cm**2 + int_fwhm_cm**2)
    sigma_b = fwhm_at_face_cm * FWHM2sigma

    sigma_fit_params = (sigma_a, sigma_b)

    # Standard linear fit
    sigma_fit = lambda r, a, b: a * r + b

    # =========================================================================
    # PARAMETER EXPLANATIONS (2-Parameter Model)
    # -------------------------------------------------------------------------
    # a (sigma_a) : Dimensionless. The rate of geometric cone expansion (D / L_eff).
    # b (sigma_b) : cm. The total combined blur physically present at distance 0,
    #               computed as sqrt(D^2 + Intrinsic^2).
    # =========================================================================

    return sigma_fit_params, sigma_fit


def create_physics_psf_3param(hole_diameter_mm, hole_length_mm, intrinsic_fwhm_mm):
    # 1. Force everything to PyTomography's native unit: Centimeters
    hole_diam_cm = hole_diameter_mm / 10.0
    hole_len_cm = hole_length_mm / 10.0
    int_fwhm_cm = intrinsic_fwhm_mm / 10.0

    FWHM2sigma = 1.0 / 2.355

    # 2. Geometric Collimator Resolution: R_geo = D * (d + L) / L = (D/L)*d + D
    # Slope 'a' (dimensionless)
    collimator_slope = (hole_diam_cm / hole_len_cm) * FWHM2sigma

    # Intercept 'b' (in cm)
    collimator_intercept = hole_diam_cm * FWHM2sigma

    # Intrinsic 'c' (in cm, converted to sigma)
    intrinsic_sigma = int_fwhm_cm * FWHM2sigma

    # 3. Custom combination in quadrature
    sigma_fit = lambda r, a, b, c: np.sqrt((a * r + b) ** 2 + c**2)

    sigma_fit_params = (collimator_slope, collimator_intercept, intrinsic_sigma)

    # =========================================================================
    # PARAMETER EXPLANATIONS (3-Parameter Model)
    # -------------------------------------------------------------------------
    # a (collimator_slope) : Dimensionless. The rate of geometric cone expansion
    #                        calculated as (D / L_eff).
    # b (collimator_int)   : cm. The geometric width of the hole itself (D).
    # c (intrinsic_sigma)  : cm. The constant intrinsic blurring of the crystal.
    # =========================================================================

    return sigma_fit_params, sigma_fit


def get_psf_meta_from_json(metadata, photon_energy, min_sigmas=3):
    FWHM2sigma = 1 / (2 * np.sqrt(2 * np.log(2)))
    detector_meta = metadata["Detector Physics Data"]
    hole_diameter = detector_meta["hole_diameter"]
    hole_length = detector_meta["collimator_thickness"]
    crystal_spatial_resolution_model = detector_meta[
        "crystal_spatial_resolution_fwhm_energy_model"
    ]
    if crystal_spatial_resolution_model == "A*sqrt(B/energy)":
        crystal_spatial_resolution_model_parameters = detector_meta[
            "crystal_spatial_resolution_fwhm_energy_model_parameters"
        ]
        A = crystal_spatial_resolution_model_parameters[0]
        B = crystal_spatial_resolution_model_parameters[1]
        intrinsic_resolution = A * np.sqrt(B / photon_energy)
    else:
        raise ValueError("Unsupported crystal spatial resolution model")
    collimator_slope = hole_diameter / hole_length * FWHM2sigma
    collimator_intercept = hole_diameter * FWHM2sigma
    sigma_fit = lambda r, a, b, c: np.sqrt((a * r + b) ** 2 + c**2)
    sigma_fit_params = (collimator_slope, collimator_intercept, intrinsic_resolution)
    # WARNING : hole_diameter, hole_length, and intrinsic_resolution MUST all converted to cm
    return SPECTPSFMeta(
        sigma_fit_params=sigma_fit_params, sigma_fit=sigma_fit, min_sigmas=min_sigmas
    )


def compute_tew_scatter_estimate(
    metadata,
    index_lower,
    index_upper,
    index_peak,
    weighting_lower: float = 0.5,
    weighting_upper: float = 0.5,
    sigma_theta: float = 0,
    sigma_r: float = 0,
    sigma_z: float = 0,
    N_sigmas: int = 3,
    return_scatter_variance_estimate: bool = False,
):
    energy_data = metadata["Energy Window Data"]
    energy_window_lower_bounds = energy_data["energy_window_lower_bounds"]
    energy_window_upper_bounds = energy_data["energy_window_upper_bounds"]
    width_lower = (
        energy_window_upper_bounds[index_lower]
        - energy_window_lower_bounds[index_lower]
    )
    width_upper = (
        energy_window_upper_bounds[index_upper]
        - energy_window_lower_bounds[index_upper]
    )
    width_peak = (
        energy_window_upper_bounds[index_peak] - energy_window_lower_bounds[index_peak]
    )
    projections = pytomography_read_projections(metadata)
    projections_lower = projections[index_lower]
    projections_upper = projections[index_upper]
    _, proj_meta = pytomography_get_detector_data(metadata)
    TEW = compute_EW_scatter(
        projections_lower,
        projections_upper,
        width_lower,
        width_upper,
        width_peak,
        weighting_lower,
        weighting_upper,
        proj_meta=proj_meta,
        sigma_r=sigma_r,
        sigma_z=sigma_z,
        sigma_theta=sigma_theta,
        N_sigmas=N_sigmas,
        return_scatter_variance_estimate=return_scatter_variance_estimate,
    )
    return TEW


def compute_dew_scatter_estimate(
    metadata,
    index_scatter_window,  # Index of the single scatter window (e.g., lower scatter)
    index_peak_window,  # Index of the photopeak window
    k_factor: float = 0.5,  # The crucial 'k' factor for DEW. Default is illustrative.
    sigma_theta: float = 0,
    sigma_r: float = 0,
    sigma_z: float = 0,
    n_sigmas: int = 3,
    return_scatter_variance_estimate: bool = False,  # DEW typically doesn't yield variance in this way
):
    """
    Computes the scatter estimate in the photopeak window using the Dual Energy Window (DEW) method.

    This function implements the classic DEW approach where scatter in the photopeak is estimated
    by scaling the counts in a single scatter window by a calibrated 'k' factor.
    It's particularly suited for radionuclides like Tc-99m, though the k_factor is crucial.

    Args:
        metadata (dict): A dictionary containing metadata, including 'Energy Window Data'
                         with 'energy_window_lower_bounds' and 'energy_window_upper_bounds'.
                         Also implicitly contains information for reading projections.
        index_scatter_window (int): The index of the single scatter window in the metadata's
                                    energy window data. This is typically a lower scatter window.
        index_peak_window (int): The index of the photopeak window in the metadata's
                                 energy window data.
        k_factor (float): The empirically determined or simulated 'k' factor used to scale
                          the scatter window counts to estimate photopeak scatter.
                          This value is critical and depends on the acquisition setup.
                          A common range for Tc-99m might be 0.4 to 0.6, but needs calibration.
        sigma_theta (float): Standard deviation for angular Gaussian smoothing (in radians).
                             Applied to the scatter window projections before scaling.
        sigma_r (float): Standard deviation for radial Gaussian smoothing (in pixels).
                         Applied to the scatter window projections before scaling.
        sigma_z (float): Standard deviation for axial Gaussian smoothing (in pixels).
                         Applied to the scatter window projections before scaling.
        n_sigmas (int): Number of standard deviations for Gaussian smoothing kernel truncation.
        return_scatter_variance_estimate (bool): Not typically used for direct DEW,
                                                 included for function signature consistency.
                                                 Will always return None if True.

    Returns:
        numpy.ndarray: A 3D NumPy array representing the estimated scatter in the photopeak window,
                       with the same shape as the photopeak projections.
    """

    energy_data = metadata["Energy Window Data"]
    energy_window_lower_bounds = energy_data["energy_window_lower_bounds"]
    energy_window_upper_bounds = energy_data["energy_window_upper_bounds"]

    # Although not directly used for the DEW calculation formula,
    # it's good practice to ensure these indices are valid.
    # We'll use the 'width_peak' for potential future extensions or consistency.
    width_scatter = (
        energy_window_upper_bounds[index_scatter_window]
        - energy_window_lower_bounds[index_scatter_window]
    )
    width_peak = (
        energy_window_upper_bounds[index_peak_window]
        - energy_window_lower_bounds[index_peak_window]
    )

    # Read all projections from the metadata
    projections = pytomography_read_projections(metadata)

    # Get the specific scatter window projections
    projections_scatter = projections[index_scatter_window]

    # Get detector metadata for smoothing
    _, proj_meta = pytomography_get_detector_data(metadata)

    # Apply Gaussian smoothing to the scatter window projections if sigmas are provided
    if sigma_theta > 0 or sigma_r > 0 or sigma_z > 0:
        # Assuming pytomography.utils.gaussian_filter_projections is available
        # or you'd apply it directly using scipy.ndimage.gaussian_filter
        # As there's no direct equivalent to proj_meta handling in scipy.ndimage
        # for these specific (theta, r, z) dimensions, we'll need to define
        # how `pytomography_gaussian_filter_projections` works.
        # For simplicity, assuming a conceptual helper or direct `scipy.ndimage` application.

        # If pytomography provides a direct way to smooth based on sigma_r, sigma_z, sigma_theta,
        # you'd use that. Otherwise, you might apply standard N-D Gaussian filtering,
        # being mindful of the axes.
        # Example using a conceptual pytomography smoothing function:
        # projections_scatter_smoothed = pytomography_gaussian_filter_projections(
        #     projections_scatter,
        #     sigma_r=sigma_r,
        #     sigma_z=sigma_z,
        #     sigma_theta=sigma_theta,
        #     N_sigmas=N_sigmas,
        #     proj_meta=proj_meta # Pass proj_meta for proper dimension handling
        # )
        # For a practical example with standard scipy, you'd map sigma_r, sigma_z, sigma_theta
        # to the correct axes of the projections_scatter array.
        # Projections are typically (angle, radial_bin, axial_bin).
        # Let's use `pytomography.utils.gaussian_filter_projections` if it's what's expected.
        try:
            from pytomography.utils import gaussian_filter_projections

            projections_scatter_smoothed = gaussian_filter_projections(
                projections_scatter,
                sigma_r=sigma_r,
                sigma_z=sigma_z,
                sigma_theta=sigma_theta,
                N_sigmas=n_sigmas,
                proj_meta=proj_meta,  # Pass proj_meta for proper dimension handling
            )
        except AttributeError:
            print(
                "Warning: `pytomography.utils.gaussian_filter_projections` not found. Skipping smoothing."
            )
            print(
                "Please ensure this function is available or handle smoothing manually (e.g., using scipy.ndimage)."
            )
            projections_scatter_smoothed = projections_scatter
    else:
        projections_scatter_smoothed = projections_scatter

    # Implement the DEW scatter estimation: Scatter_peak = k_factor * Scatter_window
    DEW_scatter_estimate = k_factor * projections_scatter_smoothed

    # DEW typically doesn't provide a variance estimate directly in this way.
    # So we return None for consistency with the TEW function signature if requested.
    if return_scatter_variance_estimate:
        return DEW_scatter_estimate, None
    else:
        return DEW_scatter_estimate


def get_attenuation_map_from_json(metadata):
    attenuation_meta = metadata["Attenuation Data"]
    dimension_x = attenuation_meta["dimension_x"]
    dimension_y = attenuation_meta["dimension_y"]
    dimension_z = attenuation_meta["dimension_z"]

    # the following are not used for the moment
    voxel_size_x = attenuation_meta["voxel_size_x"]
    voxel_size_y = attenuation_meta["voxel_size_y"]
    voxel_size_z = attenuation_meta["voxel_size_z"]
    origin_x = attenuation_meta["origin_x"]
    origin_y = attenuation_meta["origin_y"]
    origin_z = attenuation_meta["origin_z"]

    # the energy is not used
    energy = attenuation_meta["energy"]

    # get the image from the raw data
    imagefile = attenuation_meta["source_file"]
    if imagefile is None:
        return None
    amap_img = sitk.ReadImage(str(metadata["folder"] / imagefile))
    amap = sitk.GetArrayFromImage(amap_img).astype(np.float32)
    amap = amap.reshape((dimension_x, dimension_y, dimension_z))

    # rotation from gate to pytomo
    amap = convert_image_gate_to_pytomo(amap)

    # we consider the attenuation map has already been resampled
    # like the projection / reconstructed object
    return torch.tensor(amap).to(pytomography.device)


def pytomography_osem_reconstruction(
    metadata,
    index_peak,
    psf_photon_energy,
    attenuation_flag,
    scatter_mode=None,
    index_lower=None,
    index_upper=None,
    n_iters=4,
    n_subsets=8,
):
    # get metadata information
    object_meta, proj_meta = pytomography_get_detector_data(metadata)

    # get projections data
    projections = pytomography_read_projections(metadata)

    # attenuation correction
    att_transform = None
    if attenuation_flag:
        amap = get_attenuation_map_from_json(metadata)
        if amap is None:
            fatal(f"No attenuation map found in metadata. Aborting.")
        att_transform = SPECTAttenuationTransform(amap)

    # PSF correction
    psf_meta = get_psf_meta_from_json(
        metadata,
        photon_energy=psf_photon_energy / g4_units.keV,
    )
    psf_transform = SPECTPSFTransform(psf_meta)

    # scatter correction (it may be None if no sc correction)
    additive_term = None
    if index_lower is None:
        index_lower = index_peak - 1
    if scatter_mode == "TEW":
        if index_upper is None:
            index_upper = index_peak + 1
        additive_term = compute_tew_scatter_estimate(
            metadata,
            index_lower=index_lower,
            index_upper=index_upper,
            index_peak=index_peak,
        )
    if scatter_mode == "DEW":
        additive_term = compute_dew_scatter_estimate(
            metadata,
            index_scatter_window=index_lower,
            index_peak_window=index_peak,
            k_factor=1,
            sigma_theta=0,
            sigma_r=0,
            sigma_z=0,
            n_sigmas=3,
        )

    # system matrix
    if attenuation_flag:
        obj = [att_transform, psf_transform]
    else:
        obj = [psf_transform]
    system_matrix = SPECTSystemMatrix(
        obj2obj_transforms=obj,
        proj2proj_transforms=[],
        object_meta=object_meta,
        proj_meta=proj_meta,
    )

    # loss function
    likelihood = PoissonLogLikelihood(
        system_matrix=system_matrix,
        projections=projections[index_peak],
        additive_term=additive_term,
    )

    # go !
    recon_algorithm = OSEM(likelihood)
    reconstructed_image = recon_algorithm(n_iters=n_iters, n_subsets=n_subsets)

    # build the final image
    # (warning spacing is in cm)
    spacing = np.array([object_meta.dx, object_meta.dy, object_meta.dz]) * g4_units.cm
    size = np.array(object_meta.shape)
    recon_arr = reconstructed_image.cpu().numpy()
    recon_arr = convert_image_pytomo_to_gate(recon_arr)
    recon_sitk = sitk.GetImageFromArray(recon_arr)
    recon_sitk.SetSpacing(spacing)

    # get the origin according to the attenuation map
    # (warning itk in mm and pytomography in cm)
    am = metadata["Attenuation Data"]
    origin = np.array([am["origin_x"], am["origin_y"], am["origin_z"]])
    origin = origin * g4_units.cm

    recon_sitk.SetOrigin(origin)

    return recon_sitk


def pytomography_build_metadata_and_attenuation_map(
    sc,
    sim,
    attenuation_energy,
    output_folder=None,
    verbose=True,
):
    """
    Here are the necessary inputs to create the metadata
    - list of detector heads: for orientation
    - Digitizer projection actor: for size and spacing
    - Digitizer energy windows actor: for energy window
    - list of projection files: for build the sinogram in pytomography orientation
    - energy for the attenuation map
    """

    # output folder for sinogram and attenuation map
    if output_folder is None:
        output_folder = sc.output_folder

    # create a new (empty) pytomography metadata file
    metadata = pytomography_new_metadata()

    # set the detector orientations
    detectors = sc.detector_config.get_detectors(sim)
    verbose and print(f"Number of detectors: {len(detectors)}")
    for detector in detectors:
        pytomography_add_detector_orientation(metadata, detector)
    nb_proj = metadata["Projection Geometry Data"]["number_of_projections"]
    verbose and print(f"Found a total of {nb_proj} projections")

    # the angle zero is on the side of the table
    metadata["Projection Geometry Data"]["starting_angle_deg"] = -90

    # set the detector size and spacing
    size = [
        sc.detector_config.size[0],
        sc.detector_config.size[1],
        sc.detector_config.size[1],
    ]
    spacing = [
        sc.detector_config.spacing[0],
        sc.detector_config.spacing[1],
        sc.detector_config.spacing[1],
    ]
    pytomography_set_detector_info(metadata, spacing, size)
    verbose and print(f"Found detector size and spacing set to {size} and {spacing}")

    # set the energy windows
    ews = sim.actor_manager.find_actors("energy_window")
    channels = ews[0].channels
    pytomography_set_energy_windows(metadata, channels)
    verbose and print(f"Found {len(channels)} energy windows")

    # create the sinogram with all the projections
    filenames = sc.detector_config.get_proj_filenames(sim)
    o = output_folder / "sinogram.mhd"
    sino = pytomography_create_sinogram(
        filenames, sc.acquisition_config.number_of_angles, o
    )
    verbose and print(f"Build sinogram with shape {sino.shape} in {o}")
    # set the raw data only for pytomography
    metadata["Projection Geometry Data"]["source_file"] = "sinogram.mhd"

    # PSF correction "Detector Physics Data"
    dpd = metadata["Detector Physics Data"]
    m = sc.detector_config.get_model_module()
    dpd.update(m.get_pytomography_detector_physics_data(sc.detector_config.collimator))
    dpd["isotope_name"] = sc.source_config.radionuclide

    # crystal mode
    known_crystal_models = ["intevo"]  # , "nm670"]
    if sc.detector_config.model not in known_crystal_models:
        warning(f"Unknown crystal model: {sc.detector_config.model}")
        warning(f'the crystal parameters are set by default like "intevo"')

    if sc.detector_config.model == "intevo":
        dpd["crystal_spatial_resolution_fwhm_energy_model"] = "A*sqrt(B/energy)"
        dpd["crystal_spatial_resolution_fwhm_energy_model_parameters"] = [0.36, 140.5]
        dpd["crystal_energy_resolution_fwhm_pct_energy_model"] = "A*sqrt(B/energy)"
        dpd["crystal_energy_resolution_fwhm_pct_energy_model_parameters"] = [9.9, 140.5]

    if sc.detector_config.model == "nm670":
        dpd["crystal_spatial_resolution_fwhm_energy_model"] = "A*sqrt(B/energy)"
        dpd["crystal_spatial_resolution_fwhm_energy_model_parameters"] = [0.3, 140.5]
        dpd["crystal_energy_resolution_fwhm_pct_energy_model"] = "A*sqrt(B/energy)"
        dpd["crystal_energy_resolution_fwhm_pct_energy_model_parameters"] = [6.3, 140.5]

    # attenuation correction
    if sc.phantom_config.image is not None:
        # read CT image and resample like the reconstructed image
        # for the moment MUST be same size and spacing than the projection images
        # Important: take into account the translation of the phantom!
        create_attenuation_image(
            sc.phantom_config.image,
            attenuation_energy,
            output_folder / "mumap.mhd",
            size,
            spacing,
            translation=sc.phantom_config.translation,
            verbose=True,
        )
        pytomography_set_attenuation_data(
            metadata,
            attenuation_energy,
            output_folder / "mumap.mhd",
            translation=sc.phantom_config.translation,
            verbose=True,
        )
        verbose and print(
            f"Build attenuation map with shape {size} in {output_folder / 'mumap.mhd'}"
        )

    return metadata


class _ConfigBlock:
    """Base class for parameter blocks to handle dict conversion."""

    def to_dict(self):
        # We only return public attributes
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

    def __str__(self):
        lines = [f"[{self.__class__.__name__}]"]
        for k, v in self.to_dict().items():
            if isinstance(v, np.ndarray):
                # Print arrays concisely (e.g., shape and a few elements)
                arr_str = np.array2string(v, precision=2, separator=", ", threshold=4)
                lines.append(f"  {k:<15}: {arr_str} (shape: {v.shape})")
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], Path):
                # Format lists of paths cleanly
                lines.append(f"  {k:<15}: [")
                for p in v:
                    lines.append(f"    {p}")
                lines.append("  ]")
            else:
                lines.append(f"  {k:<15}: {v}")
        return "\n".join(lines)


class AcquisitionBlock(_ConfigBlock):
    def __init__(self):
        self.filenames = []
        self.angles = None
        self.radii = None
        self.size = None
        self.spacing = None
        self.num_channels = None
        self.index_peak = None
        self.isocenter = [0.0, 0.0, 0.0]

    def initialize_and_validate(self):
        if not self.filenames:
            raise ValueError("No acquisition filenames provided.")

        reader = sitk.ImageFileReader()
        reader.SetFileName(str(self.filenames[0]))
        reader.ReadImageInformation()

        proj_size = reader.GetSize()
        proj_spacing = reader.GetSpacing()

        # Auto-infer
        if getattr(self, "size", None) is None:
            self.size = [proj_size[0], proj_size[1]]
        if getattr(self, "spacing", None) is None:
            self.spacing = [proj_spacing[0], proj_spacing[1]]

        self.num_channels = len(self.filenames)

        if self.angles is not None and len(self.angles) != proj_size[2]:
            raise ValueError(
                f"Angles length ({len(self.angles)}) != projection depth ({proj_size[2]})."
            )

        if self.index_peak is None or self.index_peak is False:
            raise ValueError(
                f"Peak index ({self.index_peak}) must be a positive integer"
            )

        if self.index_peak < 0 or self.index_peak > self.num_channels:
            raise ValueError(
                f"Peak index ({self.index_peak}) out of range for number of channels ({self.num_channels}."
            )

        # Ensure isocenter is a 3D list/array
        self.isocenter = list(self.isocenter)
        if len(self.isocenter) != 3:
            raise ValueError(
                f"Isocenter must be a 3D coordinate, got: {self.isocenter}"
            )


class ReconstructionBlock(_ConfigBlock):
    def __init__(self):
        self.template_filename = None
        self.final_size = None
        self.final_spacing = None
        self.final_origin = None

    def initialize_and_validate(self):
        # Option A: User provided a reference image
        if self.template_filename is not None:
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(self.template_filename))
            reader.ReadImageInformation()

            inferred_size = list(reader.GetSize())
            inferred_spacing = list(reader.GetSpacing())
            inferred_origin = list(reader.GetOrigin())

            # Warn if manual parameters were also set and conflict with the file
            if self.final_size is not None and list(self.final_size) != inferred_size:
                warnings.warn(
                    f"Overriding manual final_size {self.final_size} with reference file size {inferred_size}"
                )

            self.final_size = inferred_size
            self.final_spacing = inferred_spacing
            self.final_origin = inferred_origin

        # Option B: User provided explicit manual parameters
        else:
            if (
                self.final_size is None
                or self.final_spacing is None
                or self.final_origin is None
            ):
                raise ValueError(
                    "Reconstruction grid parameters are incomplete. "
                    "You must provide EITHER 'filename' OR all three of "
                    "('final_size', 'final_spacing', 'final_origin')."
                )

            # Coerce to standard lists for consistent JSON serialization downstream
            self.final_size = list(self.final_size)
            self.final_spacing = list(self.final_spacing)
            self.final_origin = list(self.final_origin)

            # Basic sanity check on the shapes
            if (
                len(self.final_size) != 3
                or len(self.final_spacing) != 3
                or len(self.final_origin) != 3
            ):
                raise ValueError(
                    "Reconstruction final_size, final_spacing, and final_origin must all be 3D lists or arrays."
                )


class MumapBlock(_ConfigBlock):
    def __init__(self):
        self.filename = None
        # start with "_" = computed
        self._size = None
        self._spacing = None
        self._origin = None

    def initialize_and_validate(self):
        if self.filename is not None:
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(self.filename))
            reader.ReadImageInformation()

            # Store these temporarily/internally for the main adapter to check
            self._size = list(reader.GetSize())
            self._spacing = list(reader.GetSpacing())
            self._origin = list(reader.GetOrigin())

    def resample_like_working_grid(self, work_ref_img):
        mu_img = sitk.ReadImage(str(self.filename))

        # Resample Mumap to the strict Working Grid
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(work_ref_img)
        resampler.SetInterpolator(
            sitk.sitkLinear
        )  # Crucial for continuous attenuation values
        resampler.SetDefaultPixelValue(0.0)  # Air outside bounds
        mu_work = resampler.Execute(mu_img)

        mu_arr = sitk.GetArrayFromImage(mu_work)
        mu_arr_pt = convert_image_gate_to_pytomo(mu_arr)
        return mu_arr_pt


class PSFBlock(_ConfigBlock):
    def __init__(self):
        self.sigma_fit_params = None
        # String identifier (e.g., "3_param") or a callable.
        # Callables will trigger a warning on JSON dump.
        self.sigma_fit = None

    def initialize_and_validate(self):
        if self.sigma_fit_params is not None:
            # Rehydrate the function if it's the standard string identifier
            if self.sigma_fit == "3_param":
                self.sigma_fit = lambda r, a, b, c: np.sqrt((a * r + b) ** 2 + c**2)
            elif self.sigma_fit == "2_param":
                self.sigma_fit = lambda r, a, b: a * r + b
            elif callable(self.sigma_fit):
                pass
            else:
                raise ValueError(f"Unknown PSF sigma_fit model: {self.sigma_fit}")


class ScatterCorrectionBlock(_ConfigBlock):
    def __init__(self):
        self.mode = None
        self.index_upper = None
        self.index_lower = None
        self.w_peak_kev = None
        self.w_lower_kev = None
        self.w_upper_kev = None


class AdapterEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy arrays, Paths, and functions."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Path):
            return str(obj)
        if callable(obj):
            warning_msg = (
                f"Custom function '{obj.__name__}' detected. It will not be serialized."
            )
            warnings.warn(warning_msg)
            return f"ERROR: <function {obj.__name__} (not serializable)>"
        if isinstance(obj, _ConfigBlock):
            return obj.to_dict()
        return super().default(obj)


class GateToPyTomographyAdapter:
    def __init__(self):
        self.acquisition = AcquisitionBlock()
        self.reconstruction = ReconstructionBlock()
        self.mumap = MumapBlock()
        self.psf = PSFBlock()
        self.scatter_correction = ScatterCorrectionBlock()

    def __str__(self):
        blocks = [
            self.acquisition,
            self.reconstruction,
            self.mumap,
            self.psf,
            self.scatter_correction,
        ]
        body = "\n\n".join(str(block) for block in blocks)

        return body

    def to_dict(self):
        """Converts the entire adapter state into a dictionary."""
        return {
            "acquisition": self.acquisition,
            "reconstruction": self.reconstruction,
            "mumap": self.mumap,
            "psf": self.psf,
            "scatter_correction": self.scatter_correction,
        }

    def dump(self, filepath):
        """Serializes the configuration to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4, cls=AdapterEncoder)

    @classmethod
    def load(cls, filepath):
        """(Optional) Rehydrates the adapter from a JSON file."""
        filepath = Path(filepath)
        with open(filepath, "r") as f:
            data = json.load(f)

        adapter = cls()

        # Helper to safely map dictionaries back to block attributes
        def populate_block(block, data_dict):
            if not data_dict:
                return
            for k, v in data_dict.items():
                # Convert strings back to numpy arrays where expected
                if k in ["angles", "radii"] and v is not None:
                    setattr(block, k, np.array(v))
                # Convert path strings back to Path objects
                elif "filename" in k and v is not None:
                    if isinstance(v, list):
                        setattr(block, k, [Path(p) for p in v])
                    else:
                        setattr(block, k, Path(v))
                else:
                    setattr(block, k, v)

        populate_block(adapter.acquisition, data.get("acquisition"))
        populate_block(adapter.reconstruction, data.get("reconstruction"))
        populate_block(adapter.mumap, data.get("mumap"))
        populate_block(adapter.psf, data.get("psf"))
        populate_block(adapter.scatter_correction, data.get("scatter_correction"))

        return adapter

    def initialize_and_validate(self):
        """Triggers block validations and ensures global spatial consistency."""

        # 1. Initialize individual blocks
        self.acquisition.initialize_and_validate()
        self.reconstruction.initialize_and_validate()
        self.mumap.initialize_and_validate()
        self.psf.initialize_and_validate()
        # self.scatter_correction.initialize_and_validate()

        # 2. Cross-block validation: Mumap vs Reconstruction Grid
        if self.mumap.filename is not None:
            if (
                not np.allclose(
                    self.mumap._spacing, self.reconstruction.final_spacing, atol=1e-3
                )
                or not np.allclose(
                    self.mumap._origin, self.reconstruction.final_origin, atol=1e-3
                )
                or self.mumap._size != self.reconstruction.final_size
            ):
                warnings.warn(
                    "Mumap geometry (size, spacing, origin) does not strictly match the "
                    "reconstruction grid! This breaks sub-pixel alignment."
                )

    def reconstruct_osem(self, iterations=4, subsets=8, device="auto", verbose=False):
        """
        Executes the OSEM reconstruction using PyTomography.
        Enforces a strict Working Grid for physics accuracy and resamples to the Final Grid.
        """

        # ---------------------------------------------------------
        # 1. Device Setup
        # ---------------------------------------------------------
        if device == "auto":
            # Trust PyTomography's auto-detection (handles CUDA, MPS, and CPU)
            device = pytomography.device
        else:
            device = torch.device(device)
            # Synchronize PyTomography's global device with the user's choice
            pytomography.device = device
        verbose and print(f"Starting reconstruction on device: {device}")

        # need initialize before
        self.initialize_and_validate()

        # Enforce isotropic
        if self.acquisition.size[0] != self.acquisition.size[1]:
            raise ValueError(
                f"Acquisition size must be isotropic, "
                f"while it is {self.acquisition.size[0]}x{self.acquisition.size[1]}"
            )
        if self.acquisition.spacing[0] != self.acquisition.spacing[1]:
            raise ValueError(
                f"Acquisition spacing must be isotropic, "
                f"while it is {self.acquisition.spacing[0]}x{self.acquisition.spacing[1]}"
            )

        # ---------------------------------------------------------
        # 2. Define the Strict Working Grid (in mm for ITK)
        # ---------------------------------------------------------
        # Nx = Ny = size_u, Nz = size_v
        work_size = [
            self.acquisition.size[0],
            self.acquisition.size[0],
            self.acquisition.size[1],
        ]
        work_spacing = [
            self.acquisition.spacing[0],
            self.acquisition.spacing[0],
            self.acquisition.spacing[1],
        ]

        # Exact geometric center of the voxels, shifted by the physical isocenter
        work_origin = [
            -(work_size[0] - 1) * work_spacing[0] / 2.0 + self.acquisition.isocenter[0],
            -(work_size[1] - 1) * work_spacing[1] / 2.0 + self.acquisition.isocenter[1],
            -(work_size[2] - 1) * work_spacing[2] / 2.0 + self.acquisition.isocenter[2],
        ]

        # Create an empty ITK image to act as the spatial reference for the Working Grid
        work_ref_img = sitk.Image(work_size, sitk.sitkFloat32)
        work_ref_img.SetSpacing(work_spacing)
        work_ref_img.SetOrigin(work_origin)

        # ---------------------------------------------------------
        # 3. PyTomography Metadata Setup (Unit Conversion: mm -> cm)
        # ---------------------------------------------------------
        dr_cm = [work_spacing[0] / 10.0, work_spacing[1] / 10.0, work_spacing[2] / 10.0]
        object_meta = SPECTObjectMeta(dr=dr_cm, shape=work_size)

        proj_dr_cm = [
            self.acquisition.spacing[0] / 10.0,
            self.acquisition.spacing[1] / 10.0,
        ]
        proj_meta = SPECTProjMeta(
            projection_shape=(self.acquisition.size[0], self.acquisition.size[1]),
            dr=proj_dr_cm,
            angles=self.acquisition.angles,  # Assumed degrees
            radii=self.acquisition.radii / 10.0,  # convert to cm
        )

        # ---------------------------------------------------------
        # 4. Load & Rotate Sinograms
        # ---------------------------------------------------------
        sinograms_pt = []
        for filename in self.acquisition.filenames:
            img = sitk.ReadImage(str(filename))
            arr = sitk.GetArrayFromImage(img)
            # Apply PyTomography rotation: [Angles, Z, X] -> [Angles, X, Z] and Z flip
            arr_rotated = convert_sinogram_gate_to_pytomo(arr)
            sinograms_pt.append(
                torch.tensor(arr_rotated, dtype=torch.float32).to(device)
            )

        # ---------------------------------------------------------
        # 5. Build Object Transforms (Corrections)
        # ---------------------------------------------------------
        obj_transforms = []

        # -- Attenuation (Mumap) --
        if self.mumap.filename is not None:
            mu_arr_pt = self.mumap.resample_like_working_grid(work_ref_img)
            mu_tensor = torch.tensor(mu_arr_pt, dtype=torch.float32).to(device)
            att_transform = SPECTAttenuationTransform(mu_tensor)
            obj_transforms.append(att_transform)

        # -- Point Spread Function (PSF) --
        if self.psf.sigma_fit_params is not None:
            psf_meta = SPECTPSFMeta(
                sigma_fit_params=self.psf.sigma_fit_params, sigma_fit=self.psf.sigma_fit
            )
            psf_transform = SPECTPSFTransform(psf_meta)
            obj_transforms.append(psf_transform)

        # ---------------------------------------------------------
        # 6. Scatter Estimation
        # ---------------------------------------------------------
        additive_term = None
        if self.scatter_correction.mode == "TEW":
            from pytomography.utils import compute_EW_scatter

            p_lower = sinograms_pt[self.scatter_correction.index_lower]
            p_upper = sinograms_pt[self.scatter_correction.index_upper]

            # Actual width of the energy windows
            w_peak = self.scatter_correction.w_peak_kev
            w_lower = self.scatter_correction.w_lower_kev
            w_upper = self.scatter_correction.w_upper_kev

            additive_term = compute_EW_scatter(
                p_lower, p_upper, w_lower, w_upper, w_peak, proj_meta=proj_meta
            ).to(device)
        if self.scatter_correction.mode == "DEW":
            raise ValueError("DEW scatter correction is not supported yet.")

        # ---------------------------------------------------------
        # 7. System Matrix & Likelihood
        # ---------------------------------------------------------
        system_matrix = SPECTSystemMatrix(
            obj2obj_transforms=obj_transforms,
            proj2proj_transforms=[],
            object_meta=object_meta,
            proj_meta=proj_meta,
        )

        # The peak window index
        peak_idx = self.acquisition.index_peak
        print(f"Peak window index: {peak_idx} ({len(sinograms_pt)})")

        likelihood = PoissonLogLikelihood(
            system_matrix=system_matrix,
            projections=sinograms_pt[peak_idx],
            additive_term=additive_term,
        )

        # ---------------------------------------------------------
        # 8. OSEM Reconstruction
        # ---------------------------------------------------------
        verbose and print("Running OSEM...")
        recon_algorithm = OSEM(likelihood)
        recon_tensor = recon_algorithm(n_iters=iterations, n_subsets=subsets)

        # ---------------------------------------------------------
        # 9. Post-Processing: Rotate back and Resample
        # ---------------------------------------------------------
        recon_arr = recon_tensor.cpu().numpy()
        recon_arr = convert_image_pytomo_to_gate(recon_arr)

        # Convert to ITK in the Working Grid
        recon_img_work = sitk.GetImageFromArray(recon_arr)
        recon_img_work.SetSpacing(work_spacing)
        recon_img_work.SetOrigin(work_origin)

        # Define the Final Output Grid
        final_ref_img = sitk.Image(self.reconstruction.final_size, sitk.sitkFloat32)
        final_ref_img.SetSpacing(self.reconstruction.final_spacing)
        final_ref_img.SetOrigin(self.reconstruction.final_origin)

        # Resample from Working Grid -> Final Grid
        verbose and print("Resampling to final reconstruction grid...")
        final_resampler = sitk.ResampleImageFilter()
        final_resampler.SetReferenceImage(final_ref_img)
        final_resampler.SetInterpolator(sitk.sitkBSpline)
        final_resampler.SetDefaultPixelValue(0.0)
        recon_img_final = final_resampler.Execute(recon_img_work)

        # Clamp to remove negative ringing from spline interpolation
        recon_img_final = sitk.Clamp(recon_img_final, lowerBound=0.0)

        verbose and print("Reconstruction complete.")
        return recon_img_final
