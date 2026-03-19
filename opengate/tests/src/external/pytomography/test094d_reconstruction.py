#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
from opengate.contrib.spect.pytomography_helpers import *
from opengate.contrib.spect.spect_helpers import get_default_energy_windows
from opengate.image import get_image_physical_center
from test094_helpers import analyse_test094


def go():
    paths = utility.get_default_test_paths(__file__, output_folder="test099_pytomo")
    data_path = paths.data / "test099_pytomo"
    tomo_path = data_path / "tomo_4.8mm_2e7"
    output_path = paths.output / "reconstructed_i4s6.mha"

    mm = g4_units.mm
    keV = g4_units.keV

    # parameters
    num_angles = 120
    radius = 250 * mm

    # get the isocenter in the image space
    # must be the exact same phantom than the simulation
    iso_image = data_path / "iec_4.8mm.mhd"
    isocenter = get_image_physical_center(iso_image)
    print(f"Isocenter in the image space = {isocenter}")

    # create input parameters for pytomo reconstruction
    ad = GateToPyTomographyAdapter()

    # sinogram and detector
    ad.acquisition.filenames = [tomo_path / f"sinogram_{c}.mhd" for c in range(6)]
    ad.acquisition.angles = np.linspace(0, 360, num_angles, endpoint=False)
    ad.acquisition.radii = np.ones_like(ad.acquisition.angles) * radius
    ad.acquisition.index_peak = 4
    ad.acquisition.isocenter = isocenter

    # set the reconstruction grid from an example image
    # (can be any spacing, size)
    # recon_image_template = data_path / "iec_1mm.mhd"
    recon_image_template = data_path / "iec_4.8mm.mhd"
    ad.reconstruction.template_filename = recon_image_template

    # attenuation correction -> if "None" = not used
    # mu map will be resampled ; isocenter must be correct
    ad.mumap.filename = data_path / "iec_mu_208kev_1mm.mhd"
    # ad.mumap.filename = None

    # RM PSF (from theoretical computation or measured data)
    # if ad.pfs == None => not used
    # Example of theoretical computation
    p = intevo.get_geometrical_parameters()["melp"]
    sigma_fit_params, sigma_fit = create_physics_psf_3param(
        p.hole_diameter, p.collimator_length, intrinsic_fwhm_mm=3.6
    )
    ad.psf.sigma_fit_params = sigma_fit_params
    print(sigma_fit_params)
    ad.psf.sigma_fit = sigma_fit  # (cannot be dumped in json)

    # Example of empiric data
    sigma_fit_params = np.array((0.01788, 0.5158, 0.0022))
    print(sigma_fit_params)
    ad.psf.sigma_fit = "3_param"

    # scatter correction
    # if ad.scatter_correction == None => not used
    channels = get_default_energy_windows("lu177")
    ad.scatter_correction.mode = "TEW"
    ad.scatter_correction.index_upper = 5
    ad.scatter_correction.index_lower = 3
    ad.scatter_correction.w_peak_kev = (channels[4]["max"] - channels[4]["min"]) / keV
    ad.scatter_correction.w_lower_kev = (channels[3]["max"] - channels[3]["min"]) / keV
    ad.scatter_correction.w_upper_kev = (channels[5]["max"] - channels[5]["min"]) / keV

    # init
    ad.initialize_and_validate()
    print(ad)
    ad.dump(paths.output / "recon_param.json")

    # recon
    img = ad.reconstruct_osem(iterations=4, subsets=6, device="auto", verbose=True)
    sitk.WriteImage(img, str(output_path))
    print(f"reconstructed image saved to {output_path}")

    # test
    ref_mask_img = data_path / "iec_activity_1mm.mhd"
    ref_activity = data_path / "iec_activity_1mm.mhd"
    recon_img_path = output_path
    is_ok = analyse_test094(ref_mask_img, ref_activity, recon_img_path, paths.output)

    # end
    utility.test_ok(is_ok)


if __name__ == "__main__":
    go()
