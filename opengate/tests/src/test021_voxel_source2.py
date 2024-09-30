#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import itk
from scipy.spatial.transform import Rotation
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test021")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = True
    sim.g4_verbose_level = 0
    sim.g4_verbose_level_tracking = 1
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output
    print(sim)

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    #  change world size
    sim.world.size = [1.5 * m, 1 * m, 1 * m]

    # fake box #1
    fake = sim.add_volume("Box", "fake")
    fake.size = [66 * cm, 66 * cm, 66 * cm]
    fake.translation = [25 * cm, 5 * cm, 3 * cm]
    r = Rotation.from_euler("z", 5, degrees=True)
    r = r * Rotation.from_euler("y", -15, degrees=True)
    fake.rotation = r.as_matrix()

    # ---------------------------------------------------
    # CT image #1
    ct = sim.add_volume("Image", "ct")
    ct.image = str(paths.data / "empty_anisotrop.mhd")
    ct.mother = fake.name
    ct.voxel_materials = [[0, 10000000, "G4_WATER"]]  # only water
    ct.translation = [-3 * cm, 5 * cm, -2 * cm]
    r = Rotation.from_euler("x", 45, degrees=True)
    ct.rotation = r.as_matrix()

    ct_info = gate.image.read_image_info(ct.image)
    print(f"CT image origin and size: ", ct_info.origin, ct_info.size, ct_info.spacing)

    # source from image for CT #1
    source = sim.add_source("VoxelsSource", "vox_source")
    source.mother = ct.name
    source.particle = "alpha"
    source.activity = 20000 * Bq / sim.number_of_threads
    source.image = str(paths.data / "five_pixels_anisotrop.mhd")
    source.direction.type = "iso"
    source.position.translation = gate.image.get_translation_between_images_center(
        ct.image, source.image
    )
    print(f"Source wrt CT translation", source.position.translation)
    source.energy.mono = 1 * MeV
    src_info = gate.image.read_image_info(source.image)
    print(
        f"Source image origin and size: ",
        src_info.origin,
        src_info.size,
        src_info.spacing,
    )

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test021-2.mhd"
    dose.attached_to = ct
    img_info = gate.image.read_image_info(ct.image)

    """
    # test same size/spacing than source : OK
    dose.size = src_info.size
    dose.spacing = src_info.spacing
    """

    """
    # test same different spacing : OK
    dose.size = src_info.size * 2
    dose.spacing = src_info.spacing / 1.5
    """

    # test random size/spacing
    dose.size = [25, 18, 30]
    dose.spacing = [8.0, 5.0, 10.0]

    print(f"dose image:", dose.size)
    print(f"dose image:", dose.spacing)
    dose.output_coordinate_system = "attached_to_image"

    # cuts
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # test pixels in dose #1
    final_dose = dose.edep.get_data()
    s = itk.array_view_from_image(final_dose).sum()

    # loo for all source pixels (should be five)
    src = itk.imread(source.image)
    p = []
    arr = itk.array_view_from_image(src)
    for [i, j, k], flow in np.ndenumerate(src):
        if arr[i, j, k] > 0:
            p.append([k, j, i])
    # convert into dose coord system
    p_mm = [src.TransformIndexToPhysicalPoint(index) for index in p]
    p_d = [final_dose.TransformPhysicalPointToIndex(p) for p in p_mm]
    # get the values
    v = [final_dose.GetPixel(index) for index in p_d]
    print(v)

    is_ok = True
    tol = 208
    for vv, pp in zip(v, p):
        b = vv > tol
        utility.print_test(b, f"Compare value at {pp} : {vv:.2f} > {tol}] ?  {b}")
        is_ok = is_ok and b

    stats_ref = utility.read_stat_file(paths.output_ref / "stat021_ref_2.txt")
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stats, stats_ref, 0.1) and is_ok

    is_ok = (
        utility.assert_images(
            paths.output_ref / "test021-edep_2.mhd",
            dose.edep.get_output_path(),
            stats,
            tolerance=11,
            ignore_value=0,
            axis="y",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
