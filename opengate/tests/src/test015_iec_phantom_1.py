#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gatetools as gt
import itk
import numpy as np

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test015")

    # create the simulation
    sim = gate.Simulation()

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # main options
    ui = sim.user_info
    ui.visu = False
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = True
    ui.random_seed = 123654789

    # world size
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # add an iec phantom
    iec_phantom = gate_iec.add_iec_phantom(sim)
    iec_phantom.translation = [0 * cm, 0 * cm, 0 * cm]

    # output filename
    f = paths.output / "test015_iec_1.mhd"

    # FIXME: this should be implemented as part of Gate
    # voxelize the iec
    with gate.engines.SimulationEngine(sim) as se:
        image = gate.image.create_image_with_volume_extent(
            sim, iec_phantom.name, spacing=[3, 3, 3], margin=1
        )
        labels, image = gate.image.voxelize_volume(se, image)
        print(f"Labels : ")
        for l in labels:
            print(f"{l} = {labels[l]}")
        # rotate the IEC to be like the reference CT
        # 1) rotation 180 around X to be like in the iec 61217 coordinate system
        # 2) rotation 180 around Y because we put the phantom in that orientation on the table
        # (in reality there is an additional tiny rotation around Z, maybe 3 deg, but we don't care here)
        image = gt.applyTransformation(
            input=image, force_resample=True, adaptive=True, rotation=(180, 180, 0)
        )
        # the translation is computed as follows:
        # ref point in ref image  : 10 -30 477
        # ref point in test image : 3 153 27
        rp_ri = np.array([10, -30, 477])
        rp_ti = np.array([3, 153, 27])
        t = rp_ri - rp_ti
        t = np.array(list(image.GetOrigin())) + t
        image.SetOrigin(t)
        print(f"Write image {f}")
        itk.imwrite(image, str(f))

    # compare image
    print("Image can be compared with : ")
    gate.exception.warning(f"vv {paths.output_ref / 'iec_ct_3mm.mhd '} --fusion {f}")

    # Comparison with reference
    rf = paths.output_ref / "test015_iec_1.mhd"
    print(f"Reference image : {rf}")
    print(f"Computed  image : {f}")
    is_ok = gate.image.compare_itk_image(rf, f)
    utility.print_test(is_ok, "Compare images")
    utility.test_ok(is_ok)
