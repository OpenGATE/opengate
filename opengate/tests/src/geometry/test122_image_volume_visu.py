#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visualisation of an image volume (the box and its three middle slices):
- the intensity window of the slices (visu_window, default: 0.5 and 99.9
  percentiles, so that a few extreme voxels, e.g. metal in a CT, do not make
  all the slices dark);
- the image volume can be displayed with a non-OpenGL viewer (VRML): it used
  to crash, the slice textures were created without an OpenGL context.
"""

import itk
import numpy as np

import opengate as gate
from opengate.tests import utility


def create_simulation(paths, visu_window=None):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.visu = True
    sim.visu_type = "vrml_file_only"
    sim.visu_filename = str(paths.output / "test122_image_volume.wrl")
    sim.world.size = [1 * gate.g4_units.m] * 3

    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.material = "G4_AIR"
    patient.voxel_materials = [
        [-2000, -200, "G4_AIR"],
        [-200, 300, "G4_WATER"],
        [300, 20000, "G4_BONE_COMPACT_ICRU"],
    ]
    patient.visu_window = visu_window

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 100 * gate.g4_units.keV
    source.number_of_primaries = 10
    return sim, patient


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test122")
    is_ok = True

    # default window, with a few very high values (as metal in a CT)
    sim, patient = create_simulation(paths)
    a = np.linspace(-1000, 1000, 10000)
    a[:5] = 12000
    low, high = patient.get_visu_window(a)
    b = np.isclose(low, np.percentile(a, 0.5)) and np.isclose(
        high, np.percentile(a, 99.9)
    )
    b = b and high < 1001
    utility.print_test(
        b, f"Default window from the percentiles: [{low:.1f}, {high:.1f}]"
    )
    is_ok = is_ok and b

    # a uniform image does not lead to a null window
    low, high = patient.get_visu_window(np.full(100, 7.0))
    b = high > low
    utility.print_test(b, f"Uniform image: window [{low}, {high}]")
    is_ok = is_ok and b

    # user window
    patient.visu_window = [-200, 800]
    b = patient.get_visu_window(a) == (-200, 800)
    utility.print_test(b, "User window [-200, 800]")
    is_ok = is_ok and b

    # invalid user window
    for w in [[800, -200], [1, 2, 3]]:
        patient.visu_window = w
        try:
            patient.get_visu_window(a)
            b = False
        except Exception:
            b = True
        utility.print_test(b, f"Invalid window {w} is refused")
        is_ok = is_ok and b

    # run with a VRML file: the slices are windowed in [0, 1], and the image
    # volume does not crash the (non-OpenGL) VRML viewer
    sim, patient = create_simulation(paths, visu_window=[-200, 800])
    vrml = paths.output / "test122_image_volume.wrl"
    vrml.unlink(missing_ok=True)
    sim.run(start_new_process=False)
    b = vrml.is_file() and vrml.stat().st_size > 0
    utility.print_test(b, f"VRML file written: {vrml}")
    is_ok = is_ok and b

    # with VRML, the image volume is written as a single box, without voxels
    content = vrml.read_text() if b else ""
    b = "SOLID: patient:0" in content and "patient_Z" not in content
    utility.print_test(b, "VRML: the image volume is a box, the voxels are not written")
    is_ok = is_ok and b

    image = itk.GetArrayFromImage(itk.imread(str(paths.data / "patient-4mm.mhd")))
    expected = np.clip((image[image.shape[0] // 2] + 200) / 1000, 0, 1)
    s = np.array(patient.get_visu_slices(image)[0])
    b = s.min() >= 0 and s.max() <= 1 and np.allclose(s, expected.reshape(-1))
    utility.print_test(b, f"Slice windowed in [0, 1]: min {s.min()} max {s.max()}")
    is_ok = is_ok and b

    utility.test_ok(is_ok)
