import pytomography
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta
from pytomography.transforms.SPECT import SPECTPSFTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM
from pytomography.io.SPECT import dicom

import torch
import SimpleITK as sitk
import numpy as np


def osem_pytomography(sinogram, angles_deg, radii_cm, options):
    # convert sinogram to torch
    arr = sitk.GetArrayViewFromImage(sinogram)
    projections = torch.tensor(arr.copy()).to(pytomography.device).swapaxes(1, 2)

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

    # attenuation modeling
    # FIXME

    # PSF information
    psf_meta = dicom.get_psfmeta_from_scanner_params(
        options["collimator_name"],
        options["energy_kev"],
        intrinsic_resolution=options["intrinsic_resolution_cm"],
    )
    psf_transform = SPECTPSFTransform(psf_meta)

    # scatter correction
    # FIXME

    # Build the system matrix
    system_matrix = SPECTSystemMatrix(
        obj2obj_transforms=[psf_transform],
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
