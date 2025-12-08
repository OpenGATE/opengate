#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import itk

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="test089_geometries"
    )

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm
    deg = gate.g4_units.deg

    # colors
    colors = {
        "cyan": [0, 1, 1, 1],
        "grey": [0.7, 0.7, 0.7, 1],
        "yellow": [1, 1, 0, 1],
        "green": [0, 1, 0, 1],
        "red": [1, 0, 0, 1],
        "pink": [1, 0.75, 0.79, 1],
        "orange": [1, 0.5, 0, 1],
        "blue": [0, 0, 1, 1],
        "black": [0, 0, 0, 1],
        "white": [1, 1, 1, 1],
    }

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.output_dir = paths.output

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.visu_type = "vrml"
    ui.random_seed = "auto"
    ui.number_of_threads = 1

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # change world size
    world = sim.world
    world.size = [0.5 * m, 0.5 * m, 0.5 * m]

    # 2 cm side water box
    vol1 = sim.add_volume("Box", "vol1name")
    vol1.size = [2 * cm, 2 * cm, 2 * cm]
    vol1.translation = [0 * cm, 0 * cm, 0 * cm]
    vol1.material = "G4_WATER"
    vol1.color = colors["cyan"]

    # Half water shell centered at (0,5,0) along X, Y and Z
    vol2 = sim.add_volume("Sphere", "vol2name")
    vol2.rmin = 1 * cm
    vol2.rmax = 2 * cm
    vol2.stheta = 0 * deg
    vol2.dtheta = 90 * deg
    vol2.sphi = 0 * deg
    vol2.dphi = 360 * deg
    vol2.translation = [0 * cm, 5 * cm, 0 * cm]
    vol2.material = "G4_TISSUE_SOFT_ICRP"
    vol2.color = colors["yellow"]

    # Half 6 cm height concrete cylinder centered at (0, 10,0) cm in X, Y and Z
    vol3 = sim.add_volume("Tubs", "vol3name")
    vol3.rmin = 0.5 * cm
    vol3.rmax = 1 * cm
    vol3.dz = 3 * cm
    vol3.sphi = 0 * deg
    vol3.dphi = 180 * deg
    vol3.translation = [0 * cm, 10 * cm, 0 * cm]
    vol3.material = "G4_BRAIN_ICRP"
    vol3.color = colors["green"]

    # Trapezoid
    vol4 = sim.add_volume("Trap", "vol4name")
    vol4.dz = 60 * mm
    vol4.theta = 20 * deg
    vol4.phi = 5 * deg
    vol4.dy1 = 40 * mm
    vol4.dx1 = 30 * mm
    vol4.dx2 = 40 * mm
    vol4.alp1 = 10 * deg
    vol4.dy2 = 16 * mm
    vol4.dx3 = 10 * mm
    vol4.dx4 = 14 * mm
    vol4.alp2 = 10 * deg
    vol4.translation = [0 * cm, 0 * cm, -10 * cm]
    vol4.material = "G4_CONCRETE"
    vol4.color = colors["red"]

    # Trapezoid
    vol5 = sim.add_volume("Trd", "vol5name")
    vol5.dx1 = 30 * mm
    vol5.dx2 = 40 * mm
    vol5.dy1 = 10 * mm
    vol5.dy2 = 16 * mm
    vol5.dz = 10 * mm
    vol5.translation = [0 * cm, 7 * cm, -10 * cm]
    vol5.material = "G4_KAPTON"
    vol5.color = colors["pink"]

    # Polyhedra
    vol6 = sim.add_volume("Polyhedra", "vol6name")
    vol6.phi_start = 0 * deg
    vol6.phi_total = 360 * deg
    vol6.num_side = 6
    vol6.num_zplanes = 2
    vol6.zplane = [-2.5 * mm, 2.5 * mm]
    vol6.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    vol6.radius_outer = [0.15 * mm] * 6
    vol6.translation = [0 * cm, 13 * cm, -10 * cm]
    vol6.material = "G4_LUNG_ICRP"
    vol6.color = colors["orange"]

    # Cons
    vol7 = sim.add_volume("Cons", "vol7name")
    vol7.rmin1 = 0 * mm
    vol7.rmax1 = 2 * cm
    vol7.rmin2 = 2 * cm
    vol7.rmax2 = 4 * cm
    vol7.dz = 5 * cm
    vol7.sphi = 0 * deg
    vol7.dphi = 270 * deg
    vol7.translation = [0 * cm, 18 * cm, -10 * cm]
    vol7.material = "G4_PARAFFIN"
    vol7.color = colors["blue"]

    # Hexagon
    vol8 = sim.add_volume("Hexagon", "vol8name")
    vol8.height = 3 * cm
    vol8.radius = 2 * cm
    vol8.translation = [0 * cm, 18 * cm, 10 * cm]
    vol8.material = "Adipose"
    vol8.color = colors["black"]

    # Ellipsoid
    vol9 = sim.add_volume("Ellipsoid", "vol9name")
    vol9.xSemiAxis = 4 * cm
    vol9.ySemiAxis = 2 * cm
    vol9.zSemiAxis = 6 * cm
    vol9.zBottomCut = 1 * cm
    vol9.zTopCut = 4 * cm
    vol9.translation = [0 * cm, 13 * cm, 10 * cm]
    vol9.material = "Muscle"
    vol9.color = colors["white"]

    # Image Volume example in test009_voxels.py
    # Boolean Volume example in test016_bool_volumes.py
    # Repeatable Volume example in test017_repeatable.py
    # Tesselated Volume example in test067_tesselated_volume.py

    labels, image = sim.voxelize_geometry(extent="Auto", spacing=(2, 2, 2), margin=1)
    itk.imwrite(image, paths.output / "test089_geometries.mhd")

    # physics

    # source

    # dose actor

    # add stat actor

    # start simulation
    sim.run()

    # compare with ref
    ok = utility.assert_images(
        paths.output_ref / "test089_geometries.mhd",
        paths.output / "test089_geometries.mhd",
        tolerance=1e-5,
        sum_tolerance=1e-5,
    )
    # print results at the end
    utility.test_ok(ok)
