#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.contrib.spect.pytomography_helpers import *
from opengate.tests import utility
import subprocess


def main(dependency="test094b_spect_build_pytomography.py"):

    paths = utility.get_default_test_paths(
        __file__, None, output_folder="test094_pytomography"
    )

    # The test needs the output of the other tests
    if not os.path.isfile(paths.output / "sinogram.raw"):
        subdir = os.path.dirname(__file__.relative_to(paths.current))
        subprocess.call(["python", paths.current / subdir / dependency])

    # read the metadata file
    json_file = paths.output / "pytomography_gate.json"
    metadata = pytomography_read_metadata(json_file)

    # reconstruction
    keV = g4_units.keV
    img = pytomography_osem_reconstruction(
        metadata,
        index_peak=4,
        psf_photon_energy=208 * keV,
        attenuation_flag=True,
        scatter_mode="TEW",
        n_iters=4,
        n_subsets=6,
    )

    # write the image
    output = paths.output / "reconstructed.mhd"
    print(f"Save reconstructed image in {output}")
    sitk.WriteImage(img, output)

    # compare the image with the reference reconstructed one
    ref_output = paths.output_ref / "reconstructed.mhd"
    ref = sitk.ReadImage(ref_output)

    diff = sitk.GetArrayFromImage(sitk.Abs(ref - img))
    print(f"Max diff: {np.max(diff)}")
    # assert np.max(diff) < 1e-3, "Error in the reconstructed image"

    is_ok = utility.assert_images(
        ref_output,
        output,
        stats=None,
        tolerance=0.1,
        fig_name=paths.output / "094.png",
        sad_profile_tolerance=0.1,
    )

    print("Check with :")
    print(
        "vv ../data/ct_5mm.mhd --fusion ../data/3_sources_5mm_v2.mhd ../data/ct_5mm.mhd --fusion ../output/test094_pytomography/reconstructed.mhd --linkall"
    )

    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
