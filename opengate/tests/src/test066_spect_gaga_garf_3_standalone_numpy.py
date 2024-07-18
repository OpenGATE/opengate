#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests import utility
import gaga_phsp as gaga
import garf
import itk
from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.contrib.spect import ge_discovery_nm670
import time
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test066")
    output_path = paths.output

    # create the simulation
    simu_name = "test066_3_standalone_numpy"
    g = paths.data / "gate"

    # info about ge nm670
    mm = gate.g4_units.mm
    head_radius = 280 * mm
    pos, crystal_dist, psd = (
        ge_discovery_nm670.compute_plane_position_and_distance_to_crystal("lehr")
    )

    # parameters
    activity_source = paths.data / "iec_source_same_spheres_2mm.mhd"
    gaga_pth_filename = (
        g / "gate_test038_gan_phsp_spect" / "pth2" / "test001_GP_0GP_10_50000.pth"
    )
    garf_pth_filename = g / "gate_test043_garf" / "data" / "pth" / "arf_Tc99m_v3.pth"

    # Initial rotation of the iec -> X90 inverted
    r_iec = Rotation.from_euler("x", -90, degrees=True)

    # Initial rotation angle of the head
    r = Rotation.from_euler("x", 90, degrees=True)
    r = r * r_iec

    # garf parameters
    garf_detector = garf.GarfDetector()
    garf_detector.pth_filename = garf_pth_filename
    garf_detector.radius = head_radius
    garf_detector.crystal_distance = crystal_dist
    garf_detector.image_size = [128, 128]
    garf_detector.image_spacing = np.array([3 * mm, 3 * mm])  # FIXME
    garf_detector.initial_plane_rotation = r
    garf_detector.batch_size = 1e5

    # gaga parameters
    gaga_source = gaga.GagaSource()
    gaga_source.activity_filename = activity_source
    gaga_source.pth_filename = gaga_pth_filename
    gaga_source.batch_size = 1e5
    gaga_source.backward_distance = 50 * mm
    gaga_source.cond_translation = [0, 0, 0]

    # rotations
    gantry_angles = [0, 180]
    gantry_rotations = []
    deg = gate.g4_units.deg
    for angle in gantry_angles:
        r = Rotation.from_euler("z", angle / deg, degrees=True)
        gantry_rotations.append(r)

    # initialize
    garf_detector.initialize(gantry_rotations)
    gaga_source.initialize()

    # go
    n = 127008708 / 4
    t1 = time.time()
    images = gaga_source.generate_projections_numpy(garf_detector, n)
    t2 = time.time()
    t = t2 - t1
    print(f"Computation time is {t:.2f} seconds")
    print(f"Computation PPS is {n / t:.0f} ")

    # save image
    i = 0
    for image in images:
        output = output_path / f"{simu_name}_{i}.mhd"
        print(f"Done, saving output in {output}")
        itk.imwrite(image, output)
        i += 1
