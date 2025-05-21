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

from opengate.contrib.spect.spect_config import *
from opengate.image import resample_itk_image
from opengate.contrib.dose.photon_attenuation_image_helpers import (
    create_photon_attenuation_image,
)

import pytomography
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta, SPECTPSFMeta
from pytomography.transforms.SPECT import SPECTPSFTransform, SPECTAttenuationTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM
from pytomography.io.SPECT import dicom
from pytomography.utils import compute_EW_scatter
from scipy.ndimage import affine_transform

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


def rotation_image_pytomo_to_gate(np_image, spacing=None, size=None):
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    if size is not None:
        c = size.copy()
        size[0] = c[2]
        size[1] = c[1]
        size[2] = c[0]
    if spacing is not None:
        c = size.copy()
        spacing[0] = c[2]
        spacing[1] = c[1]
        spacing[2] = c[0]
    return rotation_arr


def rotation_sinogram_pytomo_to_gate(np_image, spacing=None, size=None):
    rotation_arr = np.transpose(np_image, axes=(0, 2, 1))
    # need copy because negative stride
    rotation_arr = rotation_arr[:, :, ::-1].copy()
    if size is not None:
        c = size.copy()
        size[0] = c[0]
        size[1] = c[2]
        size[2] = c[1]
    if spacing is not None:
        c = size.copy()
        spacing[0] = c[0]
        spacing[1] = c[2]
        spacing[2] = c[1]
    return rotation_arr


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
    att_img = None
    if "attenuation_image" in options:
        att_filename = options["attenuation_image"]
        if att_filename is not None:
            print(att_filename, type(att_filename))
            if type(att_filename) is str:
                img = sitk.ReadImage(att_filename)
            else:
                img = att_filename
            att_img = img
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

    # att ?
    if att_transform is not None:
        reconstructed_object_sitk.SetOrigin(att_img.GetOrigin())

    return reconstructed_object_sitk


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
        },
    }


def pytomography_set_detector_orientation(metadata, detector):
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
    sinograms = read_projections_as_sinograms(filenames, number_of_angles)

    sino_arr = None
    for sinogram in sinograms:
        arr = sitk.GetArrayFromImage(sinogram)
        arr = np.transpose(arr, axes=(0, 2, 1))  # probably ok, like in helpers
        arr = arr[:, :, ::-1].copy()
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


def pytomography_set_attenuation_data(
    metadata,
    ct_filename,
    energy,
    attenuation_filename,
    size,
    spacing,
    translation=None,
    verbose=False,
):

    # check attenuation_filename must be mhd/raw
    attenuation_filename = Path(attenuation_filename)
    if attenuation_filename.suffix != ".mhd":
        fatal(
            f"Attenuation file must be mhd/raw, while the "
            f"extension is {attenuation_filename.suffix} ({attenuation_filename})"
        )
    raw_filename = attenuation_filename.with_suffix(".raw")

    # resample
    image = itk.imread(ct_filename)
    verbose and print(f"Resample CT image {ct_filename} to {size} and {spacing}")
    image = resample_itk_image(
        image, size, spacing, default_pixel_value=-1000, linear=False
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

    # consider the raw part of the attenuation_filename

    # information and translation
    if translation is None:
        translation = np.array([0, 0, 0])
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

    # For now assume all oriented towards the center
    radii = np.sqrt(detector_position_x**2 + detector_position_y**2)
    angles = np.arctan2(detector_position_y, detector_position_x)
    # for GATE intevo : -90 deg rotation
    angles = np.degrees(angles) - 90

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
    imagefile = geometry_meta["source_file"]
    if folder is None:
        folder = Path(metadata["folder"])
    projections = np.fromfile(folder / imagefile, dtype=np.float32)
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


def compute_TEW_scatter_estimate(
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
    amap = np.fromfile(os.path.join(metadata["folder"], imagefile), dtype=np.float32)
    amap = amap.reshape((dimension_x, dimension_y, dimension_z))

    # rotation from gate to pytomo
    print("rotation FIXME ")
    amap = np.transpose(amap, axes=(2, 1, 0))  # FIXME as a function ?

    # we consider the attenuation map has already be resampled
    # like the projection / reconstructed object
    return torch.tensor(amap).to(pytomography.device)


def pytomgraphy_osem_reconstruction(
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
        att_transform = SPECTAttenuationTransform(amap)

    # PSF correction
    psf_meta = get_psf_meta_from_json(
        metadata,
        photon_energy=psf_photon_energy / g4_units.keV,
    )
    psf_transform = SPECTPSFTransform(psf_meta)

    # scatter correction (may be None if no sc correction)
    additive_term = None
    if scatter_mode == "TEW":
        if index_lower is None:
            index_lower = index_peak - 1
        if index_upper is None:
            index_upper = index_peak + 1
        scatter_estimate = compute_TEW_scatter_estimate(
            metadata,
            index_lower=index_lower,
            index_upper=index_upper,
            index_peak=index_peak,
        )
        additive_term = scatter_estimate
    if scatter_mode == "DEW":
        print("todo")

    # FIXME complete other scatter correction

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

    # build the final sitk image
    # (warning spacing in cm)
    spacing = np.array([object_meta.dx, object_meta.dy, object_meta.dz]) * g4_units.cm
    size = np.array(object_meta.shape)
    recon_arr = reconstructed_image.cpu().numpy()
    recon_arr = rotation_image_pytomo_to_gate(recon_arr)
    recon_sitk = sitk.GetImageFromArray(recon_arr)
    recon_sitk.SetSpacing(spacing)

    # get the origin according to the attenuation map
    # (warning itk in mm and pytomography in cm)
    if attenuation_flag:
        am = metadata["Attenuation Data"]
        origin = np.array([am["origin_x"], am["origin_y"], am["origin_z"]])
        tr = np.array(am["translation"])
        origin -= tr
        origin = origin * g4_units.cm
    else:
        origin = -(size * spacing) / 2.0 + spacing / 2.0
    recon_sitk.SetOrigin(origin)

    return recon_sitk
