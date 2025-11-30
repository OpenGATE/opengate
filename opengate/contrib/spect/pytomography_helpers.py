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


def rotate_np_image_to_pytomography(np_image):
    """
    Rotate a numpy image to the pytomography coordinate system.
    For example, for the attenuation map.
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    return rotation_arr


def rotate_np_pytomography_to_image(np_image):
    """
    Rotate a numpy pytomography reconstructed image to the Gate coordinate system.
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    rotation_arr = rotation_arr[:, ::-1, :].copy()
    return rotation_arr


def rotate_np_sinogram_to_pytomography(np_sinogram):
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


def pytomography_create_sinogram(filenames, number_of_angles, output_filename):
    # consider sinogram for all energy windows
    sinograms = load_and_merge_multi_head_projections(filenames, number_of_angles)
    sino_arr = None
    for sinogram in sinograms:
        arr = sitk.GetArrayFromImage(sinogram)
        arr = rotate_np_sinogram_to_pytomography(arr)
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
    verbose and print(f"Compute attenuation map for E={energy/g4_units.MeV} MeV")
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
    sigma_fit_params = [collimator_slope, collimator_intercept, intrinsic_resolution]
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
    amap = rotate_np_image_to_pytomography(amap)

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
    recon_arr = rotate_np_pytomography_to_image(recon_arr)
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
