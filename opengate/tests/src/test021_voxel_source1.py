#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import itk
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test021")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
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
    fake.size = [36 * cm, 36 * cm, 36 * cm]
    fake.translation = [25 * cm, 0, 0]
    r = Rotation.from_euler("y", -25, degrees=True)
    r = r * Rotation.from_euler("x", -35, degrees=True)
    fake.rotation = r.as_matrix()

    # ---------------------------------------------------
    # CT image #1
    ct = sim.add_volume("Image", "ct")
    ct.image = str(paths.data / "10x10x10.mhd")
    ct.mother = fake.name
    ct.voxel_materials = [[0, 10, "G4_WATER"]]
    ct.translation = [-3 * cm, 0, 0]
    r = Rotation.from_euler("z", 45, degrees=True)
    ct.rotation = r.as_matrix()

    ct_info = gate.image.read_image_info(ct.image)
    print(f"CT image origin and size: ", ct_info.origin, ct_info.size, ct_info.spacing)

    # source from image for CT #1
    source = sim.add_source("VoxelsSource", "vox_source")
    source.mother = ct.name
    source.particle = "alpha"
    source.activity = 10000 * Bq / sim.number_of_threads
    source.image = str(paths.data / "five_pixels_10.mhd")
    source.direction.type = "iso"
    source.position.translation = gate.image.get_translation_between_images_center(
        ct.image, source.image
    )
    print(f"Source wrt CT 10x10x10 translation", source.position.translation)
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
    dose.edep.output_filename = "test021-1.mhd"
    # we do not need to write the image to disk
    # because we can get it directly from the actor after the simulation
    dose.edep.write_to_disk = False
    dose.attached_to = ct.name
    img_info = gate.image.read_image_info(ct.image)
    dose.size = img_info.size
    dose.spacing = img_info.spacing
    dose.output_coordinate_system = "attached_to_image"

    # cuts
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm
    # sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # test pixels in dose #1
    # test pixels in dose #1
    d_even = dose.edep.get_data()
    s = itk.array_view_from_image(d_even).sum()
    v0 = d_even.GetPixel([5, 5, 5])
    v1 = d_even.GetPixel([1, 5, 5])
    v2 = d_even.GetPixel([1, 2, 5])
    v3 = d_even.GetPixel([5, 2, 5])
    v4 = d_even.GetPixel([6, 2, 5])
    tol = 0.15
    ss = v0 + v1 + v2 + v3 + v4

    def t(s, v):
        diff = abs(s - v) / s
        b = diff < tol
        p = diff * 100.0
        utility.print_test(b, f"Image diff {s:.2f} vs {v:.2f}  -> {p:.2f}%")
        return b

    is_ok = t(s, ss)
    is_ok = t(2000, v0) and is_ok
    is_ok = t(2000, v1) and is_ok
    is_ok = t(2000, v2) and is_ok
    is_ok = t(2000, v3) and is_ok
    is_ok = t(2000, v4) and is_ok

    stats_ref = utility.read_stat_file(paths.output_ref / "stat021_ref_1.txt")
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stats, stats_ref, 0.1) and is_ok

    utility.test_ok(is_ok)
