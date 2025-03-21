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
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta
from pytomography.transforms.SPECT import SPECTPSFTransform, SPECTAttenuationTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM
from pytomography.io.SPECT import dicom

import torch
import SimpleITK as sitk
import numpy as np


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
