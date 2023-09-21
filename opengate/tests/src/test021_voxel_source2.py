#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import itk
from scipy.spatial.transform import Rotation
import gatetools as gt
import numpy as np

if __name__ == "__main__":
    paths = gate.get_default_test_paths(__file__, "")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = 1
    ui.random_seed = 123456
    print(ui)

    # add a material database
    sim.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    cm = gate.g4_units("cm")
    keV = gate.g4_units("keV")
    MeV = gate.g4_units("MeV")
    Bq = gate.g4_units("Bq")
    kBq = 1000 * Bq

    #  change world size
    world = sim.world
    world.size = [1.5 * m, 1 * m, 1 * m]

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

    ct_info = gate.read_image_info(ct.image)
    print(f"CT image origin and size: ", ct_info.origin, ct_info.size, ct_info.spacing)

    # source from image for CT #1
    source = sim.add_source("VoxelsSource", "vox_source")
    source.mother = ct.name
    source.particle = "alpha"
    source.activity = 20000 * Bq / ui.number_of_threads
    source.image = str(paths.data / "five_pixels_anisotrop.mhd")
    source.direction.type = "iso"
    source.position.translation = gate.get_translation_between_images_center(
        ct.image, source.image
    )
    print(f"Source wrt CT translation", source.position.translation)
    source.energy.mono = 1 * MeV
    src_info = gate.read_image_info(source.image)
    print(
        f"Source image origin and size: ",
        src_info.origin,
        src_info.size,
        src_info.spacing,
    )

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = str(paths.output / "test021-edep_2.mhd")
    dose.mother = ct.name
    img_info = gate.read_image_info(ct.image)

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
    dose.img_coord_system = True

    # cuts
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("Stats")
    # stat.write(paths.output_ref / "stat021_ref_2.txt")

    # test pixels in dose #1
    final_dose = itk.imread(dose.output)
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
        gate.print_test(b, f"Compare value at {pp} : {vv:.2f} > {tol}] ?  {b}")
        is_ok = is_ok and b

    stats_ref = gate.read_stat_file(paths.output_ref / "stat021_ref_2.txt")
    stats_ref.counts.run_count = ui.number_of_threads
    is_ok = gate.assert_stats(stat, stats_ref, 0.1) and is_ok

    is_ok = (
        gate.assert_images(
            paths.output_ref / "test021-edep_2.mhd",
            dose.output,
            stat,
            tolerance=11,
            ignore_value=0,
            axis="y",
        )
        and is_ok
    )

    gate.test_ok(is_ok)
