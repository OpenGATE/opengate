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

import pytomography
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta, SPECTPSFMeta
from pytomography.transforms.SPECT import SPECTPSFTransform, SPECTAttenuationTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM
from pytomography.io.SPECT import dicom
from pytomography.utils import compute_EW_scatter

import torch
import SimpleITK as sitk
import numpy as np
import json
import os
from pathlib import Path


def rotation_image_to_pytomo_coordinate(np_image, spacing=None, size=None):
    """
    Rotate image from ITK coordinate system to pytomography coordinate system (z,x,y) -> (x,y,z)

    Parameters:
    np_image : np.array
        Input image in numpy array format.
    spacing : np.array default=None
        Spacing of the image in the format [spacing_z, spacing_x, spacing_y].

    Returns:
    np.array
        The rotated image in numpy array format.
    np.array if spacing is not None
        The rotated spacing in the format [spacing_x, spacing_y, spacing_z].
    """
    if spacing is not None and size is not None:
        rotated_image = np.transpose(np_image, axes=(1, 2, 0))
        rotated_spacing = np.array([spacing[1], spacing[2], spacing[0]])
        rotated_size = np.array([size[1], size[2], size[0]])
        return rotated_image, rotated_spacing, rotated_size
    else:
        rotated_image = np.transpose(np_image, axes=(1, 2, 0))
        return rotated_image


def rotation_pytomo_to_image_coordinate(np_image, spacing=None, size=None):
    """
    Rotate image from pytomography coordinate system to ITK coordinate system (x,y,z) -> (z,x,y)

    Parameters:
    np_image : np.array
        Input image in numpy array format.
    spacing : np.array default=None
        Spacing of the image in the format [spacing_x, spacing_y, spacing_z].

    Returns:
    np.array
        The rotated image in numpy array format.
    np.array if spacing is not None
        The rotated spacing in the format [spacing_z, spacing_x, spacing_y].
    """
    if spacing is not None and size is not None:
        rotated_image = np.transpose(np_image, axes=(2, 0, 1))
        rotated_spacing = np.array([spacing[2], spacing[0], spacing[1]])
        rotated_size = np.array([size[2], size[0], size[1]])
        return rotated_image, rotated_spacing, rotated_size
    else:
        rotated_image = np.transpose(np_image, axes=(2, 0, 1))
        return rotated_image


def rotation_sinogram_to_pytomo_coordinate(np_sinogram, spacing=None, size=None):
    """
    Rotate sinogram from ITK coordinate system to pytomography coordinate system (angles,z,x) -> (angles,x,z)

    Parameters:
    np_sinogram : np.array
        Input sinogram in numpy array format.
    spacing : np.array default=None
        Spacing of the sinogram in the format [spacing_z, spacing_x].

    Returns:
    np.array
        The rotated sinogram in numpy array format.
    np.array if spacing is not None
        The rotated spacing in the format [spacing_x, spacing_z].
    """
    if spacing is not None and size is not None:
        rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
        rotated_spacing = np.array([spacing[1], spacing[0]])
        rotated_size = np.array([size[1], size[0]])
        return rotated_sinogram, rotated_spacing, rotated_size
    else:
        rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
        return rotated_sinogram


def rotation_pytomo_to_sinogram_coordinate(np_sinogram, spacing=None, size=None):
    """
    Rotate sinogram from pytomography coordinate system to ITK coordinate system (angles,x,z) -> (angles,z,x)

    Parameters:
    np_sinogram : np.array
        Input sinogram in numpy array format.
    spacing : np.array default=None
        Spacing of the sinogram in the format [spacing_x, spacing_z].

    Returns:
    np.array
        The rotated sinogram in numpy array format.
    np.array if spacing is not None
        The rotated spacing in the format [spacing_z, spacing_x].

    """
    if spacing is not None and size is not None:
        rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
        rotated_spacing = np.array([spacing[1], spacing[0]])
        rotated_size = np.array([size[1], size[0]])
        return rotated_sinogram, rotated_spacing, rotated_size
    else:
        rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
        return rotated_sinogram


def osem_pytomography(sinogram, angles_deg, radii_cm, options):
    """
    Perform OSEM (Ordered Subset Expectation Maximization) image reconstruction
    from a provided sinogram using specific tomography parameters and options.

    Reconstruction is performed with pytomography library https://github.com/PyTomography

    The function constructs the necessary metadata and system matrix for SPECT
    (single-photon emission computed tomography) reconstruction, applying
    attenuation and point spread function (PSF) transformations. Before starting
    the reconstruction process, the function ensures consistency between the
    dimensions and spacing of the sinogram projections and the reconstructed
    image. It finally returns the reconstructed image as a SimpleITK image.

    Parameters:
    sinogram : SimpleITK.Image
        Input sinogram in SimpleITK image format.
    angles_deg : List[float]
        List of angles in degrees at which projections are taken.
    radii_cm : List[float]
        List of radii in centimeters for each projection.
    options : dict
        Options for the reconstruction process. Must include keys 'size',
        'spacing', 'collimator_name', 'energy_kev', 'intrinsic_resolution_cm',
        'n_iters', and 'n_subsets'.

    Returns:
    SimpleITK.Image
        The reconstructed image.
    """

    # set information about the projections
    proj_size_itk = sinogram.GetSize()[0:2]
    proj_spacing_itk = sinogram.GetSpacing()[0:2]

    # set information about the reconstructed image
    size_itk = np.array(options["size"]).astype(int)
    spacing_itk = np.array(options["spacing"])

    # convert sinogram to torch
    arr = sitk.GetArrayFromImage(sinogram)
    arr, proj_spacing, proj_size = rotation_sinogram_to_pytomo_coordinate(
        arr, proj_spacing_itk, proj_size_itk
    )
    projections = torch.tensor(arr).to(pytomography.device)

    _, spacing, size = rotation_image_to_pytomo_coordinate(
        np.zeros(size_itk), spacing=spacing_itk, size=size_itk
    )

    # set pytomography metadata
    object_meta = SPECTObjectMeta(list(spacing), list(size))
    proj_meta = SPECTProjMeta(proj_size, proj_spacing, angles_deg, radii_cm)

    # FIXME it seems that pytomography requires projection size equals to reconstructed image size
    if not np.all(proj_size == size[0:2]):
        raise ValueError(
            f"Projection size and reconstructed image size must be equal: {proj_size} != {size[0:2]}"
        )
    if not np.all(proj_spacing == spacing[0:2]):
        raise ValueError(
            f"Projection spacing and reconstructed image spacing must be equal: {proj_spacing} != {spacing[0:2]}"
        )
    if size[2] != size[0]:
        raise ValueError(
            f"Image size[2] must be equal to image size[0]: {size[2]} != {size[0]}"
        )

    # attenuation correction
    att_transform = None
    if "attenuation_image" in options:
        att_filename = options["attenuation_image"]
        if att_filename is not None:
            if type(att_filename) is str:
                img = sitk.ReadImage(att_filename)
            else:
                img = att_filename
            arr = (
                sitk.GetArrayFromImage(img).astype(np.float32) / 10
            )  # need cm-1 -> ???? FIXME

            arr = rotation_image_to_pytomo_coordinate(arr)
            attenuation_map = torch.tensor(arr).to(pytomography.device)
            att_transform = SPECTAttenuationTransform(attenuation_map=attenuation_map)

    # PSF correction
    psf_meta = dicom.get_psfmeta_from_scanner_params(
        options["collimator_name"],
        options["energy_kev"],
        intrinsic_resolution=options["intrinsic_resolution_cm"],
    )
    psf_transform = SPECTPSFTransform(psf_meta)

    # scatter correction
    # FIXME

    # Build the system matrix
    obj2obj_transforms = [psf_transform]
    if att_transform is not None:
        obj2obj_transforms = [att_transform, psf_transform]
    system_matrix = SPECTSystemMatrix(
        obj2obj_transforms=obj2obj_transforms,
        proj2proj_transforms=[],
        object_meta=object_meta,
        proj_meta=proj_meta,
    )

    # Setup OSEM
    likelihood = PoissonLogLikelihood(system_matrix, projections)
    reconstruction_algorithm = OSEM(likelihood)

    # Go !
    reconstructed_object = reconstruction_algorithm(
        n_iters=options["n_iters"], n_subsets=options["n_subsets"]
    )

    # build the final sitk image
    reconstructed_object_arr = reconstructed_object.cpu().numpy()
    reconstructed_object_arr = rotation_pytomo_to_image_coordinate(
        reconstructed_object_arr
    )
    reconstructed_object_sitk = sitk.GetImageFromArray(reconstructed_object_arr)
    reconstructed_object_sitk.SetSpacing(spacing_itk)
    origin = -(size * spacing_itk) / 2.0 + spacing_itk / 2.0
    reconstructed_object_sitk.SetOrigin(origin)

    return reconstructed_object_sitk


def pytomography_new_metadata():
    return {
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
        },
        "Energy Window Data": {
            "energy_window_lower_bounds": [],
            "energy_window_upper_bounds": [],
            "number_of_energy_windows": 0,
        },
        "Detector Physics Data": {
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
    }


def pytomography_set_detector_orientation(metadata, detector):
    geom = metadata["Projection Geometry Data"]
    for dp in detector.dynamic_params.values():
        translations = dp["translation"]
        rotations = dp["rotation"]
        for tr, rot in zip(translations, rotations):
            # translation and rotation are according to the mother volume of the detector
            geom["detector_position_x"].append(tr[0])
            geom["detector_position_y"].append(tr[1])
            geom["detector_position_z"].append(tr[2])
            # FIXME
            geom["detector_orientation_x"].append(rot[0].tolist())
            geom["detector_orientation_y"].append(rot[1].tolist())
            geom["detector_orientation_z"].append(rot[2].tolist())
        geom["number_of_projections"] += len(translations)


def pytomography_set_detector_info(metadata, pixel_size, dimension):
    geom = metadata["Projection Geometry Data"]
    geom["projection_pixel_size_r"] = pixel_size[0]
    geom["projection_pixel_size_z"] = pixel_size[1]
    geom["projection_dimension_r"] = dimension[0]
    geom["projection_dimension_z"] = dimension[1]


def pytomography_set_energy_windows(metadata, channels):
    ew = metadata["Energy Window Data"]
    for channel in channels:
        ew["energy_window_lower_bounds"].append(channel["min"])
        ew["energy_window_upper_bounds"].append(channel["max"])
        ew["number_of_energy_windows"] += 1


def get_metadata(json_file):
    with open(json_file, "r") as f:
        metadata = json.load(f)
    geometry_meta = metadata["Projection Geometry Data"]
    detector_position_x = np.array(geometry_meta["detector_position_x"])
    detector_position_y = np.array(geometry_meta["detector_position_y"])
    detector_position_z = np.array(geometry_meta["detector_position_z"])
    detector_orientation_x = np.array(geometry_meta["detector_orientation_x"])
    detector_orientation_y = np.array(geometry_meta["detector_orientation_y"])
    detector_orientation_z = np.array(geometry_meta["detector_orientation_z"])
    projection_pixel_size_r = geometry_meta["projection_pixel_size_r"]
    projection_pixel_size_z = geometry_meta["projection_pixel_size_z"]
    projection_dimension_r = geometry_meta["projection_dimension_r"]
    projection_dimension_z = geometry_meta["projection_dimension_z"]
    # For now assume all oriented towards the center
    radii = np.sqrt(detector_position_x**2 + detector_position_y**2)
    angles = np.arctan2(detector_position_y, detector_position_x)
    angles = np.degrees(angles)
    object_meta = SPECTObjectMeta(
        (projection_pixel_size_r, projection_pixel_size_r, projection_pixel_size_z),
        (projection_dimension_r, projection_dimension_r, projection_dimension_z),
    )
    proj_meta = SPECTProjMeta(
        (projection_dimension_r, projection_dimension_z),
        (projection_pixel_size_r, projection_pixel_size_z),
        angles,
        radii,
    )
    return object_meta, proj_meta


def get_projections(json_file):
    with open(json_file, "r") as f:
        metadata = json.load(f)
    object_meta, proj_meta = get_metadata(json_file)
    energy_meta = metadata["Energy Window Data"]
    number_of_energy_windows = energy_meta["number_of_energy_windows"]
    geometry_meta = metadata["Projection Geometry Data"]
    imagefile = geometry_meta["source_file"]
    projections = np.fromfile(
        os.path.join(str(Path(json_file).parent), imagefile), dtype=np.float32
    )
    projections = projections.reshape(number_of_energy_windows, *proj_meta.shape)
    projections = torch.tensor(projections).to(pytomography.device)
    return projections


def get_psf_meta_from_json(json_file, photon_energy, min_sigmas=3):
    with open(json_file, "r") as f:
        metadata = json.load(f)
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


def compute_TEW_scatter_estimate(
    json_file,
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
    with open(json_file, "r") as f:
        metadata = json.load(f)
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
    projections = get_projections(json_file)
    projections_lower = projections[index_lower]
    projections_upper = projections[index_upper]
    _, proj_meta = get_metadata(json_file)
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
