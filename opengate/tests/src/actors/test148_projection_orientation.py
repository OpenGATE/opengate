#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DigitizerProjectionActor: detector_orientation_matrix to choose the projection
plane (#301). A 60 keV pencil beam along X hits a crystal whose thickness is
along X, at (y, z) = (30, -20) mm.
- default orientation: the projection plane is XY (z is lost);
- rotation of 90 deg around Y: the image axes are -Z and Y (projection along X),
  the beam is at (20, 30) mm in the image.
"""

import itk
import numpy as np
import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility

mm = gate.g4_units.mm
keV = gate.g4_units.keV
m = gate.g4_units.m


def run(name, rotation=None):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 4321
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [10 * mm, 200 * mm, 100 * mm]  # thickness along X
    crystal.material = "G4_SODIUM_IODIDE"

    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 60 * keV
    source.position.type = "point"
    source.position.translation = [-100 * mm, 30 * mm, -20 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [1, 0, 0]
    source.number_of_primaries = 1000

    hc = sim.add_actor("DigitizerHitsCollectionActor", "hits")
    hc.attached_to = crystal
    hc.attributes = ["PostPosition", "TotalEnergyDeposit"]
    hc.root_output.write_to_disk = False

    proj = sim.add_actor("DigitizerProjectionActor", "proj")
    proj.attached_to = crystal
    proj.input_digi_collections = ["hits"]
    proj.spacing = [2 * mm, 2 * mm]
    proj.size = [128, 128]
    if rotation is not None:
        proj.detector_orientation_matrix = rotation
    proj.output_filename = f"test148_{name}.mhd"

    sim.run(start_new_process=True)

    img = itk.imread(str(proj.get_output_path("counts")))
    a = itk.array_view_from_image(img)
    k = np.unravel_index(np.argmax(a), a.shape)
    p = np.array(img.TransformIndexToPhysicalPoint([int(k[2]), int(k[1]), int(k[0])]))
    return a.sum(), p


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test148")
    tol = 2 * mm

    # default: XY plane, the beam enters the crystal at x = -5 mm, y = 30 mm
    n, p = run("default")
    b = -5 * mm <= p[0] <= 5 * mm and abs(p[1] - 30 * mm) <= tol and n > 900
    utility.print_test(b, f"Default (XY plane)   : {n:.0f} counts, max at {p[:2]}")
    is_ok = b

    # rotation around Y: image axes -Z and Y
    r = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    n, p = run("rot_y90", r)
    b = abs(p[0] - 20 * mm) <= tol and abs(p[1] - 30 * mm) <= tol and n > 900
    utility.print_test(b, f"Rotation Y (-Z,Y)    : {n:.0f} counts, max at {p[:2]}")
    is_ok = b and is_ok

    utility.test_ok(is_ok)
