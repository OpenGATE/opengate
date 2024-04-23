#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import gaga_phsp as gaga
import itk
from box import Box
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.contrib.spect import ge_discovery_nm670
import time

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    # create the simulation
    simu_name = "test066_3_standalone"
    g = paths.data / "gate"

    # info about ge nm670
    mm = gate.g4_units.mm
    head_radius = 280 * mm
    pos, crystal_dist, psd = genm670.compute_plane_position_and_distance_to_crystal(
        "lehr"
    )

    # parameters
    activity_source = paths.data / "iec_source_same_spheres_2mm.mhd"
    gaga_pth_filename = (
        g / "gate_test038_gan_phsp_spect" / "pth2" / "test001_GP_0GP_10_50000.pth"
    )
    garf_pth_filename = g / "gate_test043_garf" / "data" / "pth" / "arf_Tc99m_v3.pth"
    gaga_user_info = Box(
        {
            "pth_filename": gaga_pth_filename,
            "activity_source": activity_source,
            "batch_size": 1e5,
            "gpu_mode": "auto",
            "backward_distance": 50 * mm,
            "verbose": 0,
        }
    )
    garf_user_info = Box(
        {
            "pth_filename": garf_pth_filename,
            "image_size": [128, 128],
            "image_spacing": [3 * mm, 3 * mm],
            "plane_distance": head_radius,
            "distance_to_crystal": crystal_dist,
            "batch_size": 1e5,
            "gpu_mode": "auto",
            "verbose": 0,
            "hit_slice": False,
        }
    )

    print(f"{garf_user_info.plane_distance=}")

    # initialize gaga and garf (read the NN)
    gaga.gaga_garf_generate_spect_initialize(gaga_user_info, garf_user_info)

    # Initial rotation of the iec -> X90 inverted
    r_iec = Rotation.from_euler("x", -90, degrees=True)

    # Initial rotation angle of the head
    r = Rotation.from_euler("x", 90, degrees=True)
    r = r * r_iec
    garf_user_info.plane_rotation = r

    # define the angles
    angle_rotations = [
        Rotation.from_euler("y", 0, degrees=True),
        Rotation.from_euler("y", 180, degrees=True),  # FIXME why Y ?????
    ]

    # GO
    n = 127008708 / 4
    t1 = time.time()
    images = gaga.gaga_garf_generate_spect(
        gaga_user_info, garf_user_info, n, angle_rotations
    )
    t2 = time.time()
    t = t2 - t1
    print(f"Computation time is {t:.2f} seconds")
    print(f"Computation PPS is {n/t:.0f} ")

    # save image
    i = 0
    for image in images:
        output = output_path / f"{simu_name}_{i}.mhd"
        print(f"Done, saving output in {output}")
        itk.imwrite(image, output)
        i += 1
