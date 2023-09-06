#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import itk

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__)
    paths.data = paths.data / "t048_split_spect_projections"

    # input of 4 heads projection images, with 3 energy windows
    input_filenames = []
    for i in range(4):
        input_filenames.append(paths.data / f"ref_projection_{i}.mhd")
    print(f"Reading {len(input_filenames)} images")

    info = gate.read_image_info(input_filenames[0])
    print("Image info: ", info.size, info.spacing, info.origin)

    # compute the output images
    nb_ene = 3
    outputs = gate.split_spect_projections(input_filenames, nb_ene)

    # write them
    e = 0
    output_filenames = []
    output_filename = str(paths.output / "t048_projection.mhd")
    for o in outputs:
        f = output_filename.replace(".mhd", f"_{e}.mhd")
        itk.imwrite(o, f)
        output_filenames.append(f)
        e += 1

    # ---------------------------------------------------------------
    print()
    gate.warning("Compare image to reference")
    is_ok = True
    for i in range(nb_ene):
        is_ok = (
            gate.assert_images(
                paths.output_ref / f"t048_projection_{i}.mhd",
                output_filenames[i],
                None,
                tolerance=1e-6,
                ignore_value=0,
                axis="x",
            )
            and is_ok
        )

    gate.test_ok(is_ok)
