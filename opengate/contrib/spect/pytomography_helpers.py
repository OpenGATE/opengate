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

    # convert sinogram to torch
    arr = sitk.GetArrayFromImage(sinogram)
    projections = torch.tensor(arr).to(pytomography.device).swapaxes(1, 2)

    # set information about the projections
    proj_size = sinogram.GetSize()[0:2]
    proj_spacing = sinogram.GetSpacing()[0:2]
    proj_meta = SPECTProjMeta(proj_size, proj_spacing, angles_deg, radii_cm)

    # set information about the reconstructed image
    size = np.array(options["size"]).astype(int)
    spacing = np.array(options["spacing"])
    object_meta = SPECTObjectMeta(list(spacing), list(size))

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
            attenuation_map = torch.tensor(arr).to(pytomography.device).swapaxes(1, 2)
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
    reconstructed_object_arr = np.transpose(reconstructed_object_arr, (2, 0, 1))
    reconstructed_object_sitk = sitk.GetImageFromArray(reconstructed_object_arr)
    reconstructed_object_sitk.SetSpacing(spacing)
    origin = -(size * spacing) / 2.0 + spacing / 2.0
    reconstructed_object_sitk.SetOrigin(origin)

    return reconstructed_object_sitk
