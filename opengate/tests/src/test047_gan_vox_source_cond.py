#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test047_gan_vox_source"
    )

    """
    Data :
    gt_image_crop source_three_areas.mhd -o source_three_areas_crop.mhd
    gt_affine_transform -i source_three_areas_crop.mhd -o source_three_areas_crop_3.5mm.mhd  --newspacing 3.5 -fr -a -im NN
    """

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    # sim.visu = True
    sim.visu_type = "vrml"
    sim.number_of_threads = 1
    sim.random_seed = 123456789
    sim.output_dir = paths.output
    sim.progress_bar = True
    activity_bq = 1e6

    # visu
    if sim.visu:
        sim.number_of_threads = 1
        activity_bq = 100

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # add a fake object to test position & rotation
    fake = sim.add_volume("Box", "fake")
    fake.size = [1 * m, 1 * m, 1 * m]
    fake.translation = [5 * cm, 10 * cm, 0 * cm]
    r = Rotation.from_euler("y", 33, degrees=True)
    fake.rotation = r.as_matrix()
    fake.material = "G4_AIR"
    fake.color = [0, 0, 1, 1]  # blue

    # add an image
    f = paths.data / "ct_4mm.mhd"
    if sim.visu:
        f = paths.data / "ct_40mm.mhd"

    ct = sim.add_volume("Image", "ct")
    ct.image = f
    ct.mother = "fake"
    ct.material = "G4_AIR"
    tol = 0.1 * gcm3
    ct.voxel_materials, materials = gate.geometry.materials.HounsfieldUnit_to_material(
        sim,
        tol,
        paths.data / "Schneider2000MaterialsTable.txt",
        paths.data / "Schneider2000DensitiesTable.txt",
    )
    ct.dump_label_image = paths.output / "ct_4mm_labels.mhd"

    # condGAN source with voxelized condition
    source = sim.add_source("GANSource", "source")
    source.mother = "ct"
    source.cond_image = paths.data / "source_three_areas_crop_3.5mm.mhd"
    source.position.translation = gate.image.get_translation_between_images_center(
        str(ct.image), str(source.cond_image)
    )
    source.position.translation = source.position.translation / 2.0
    print(f"translation {source.position.translation}")
    source.particle = "alpha"
    source.activity = activity_bq * Bq / sim.number_of_threads
    source.compute_directions = True
    source.pth_filename = paths.data / "train_gaga_v001_GP_0GP_10_60000.pth"
    source.position_keys = ["PrePosition_X", "PrePosition_Y", "PrePosition_Z"]
    # source.backward_distance = 20 * cm
    # source.backward_force = True
    source.cond_debug = True
    source.direction_keys = ["PreDirection_X", "PreDirection_Y", "PreDirection_Z"]
    source.energy.mono = 1 * MeV
    source.energy_key = None
    source.weight_key = None
    source.time_key = None
    source.relative_timing = True
    source.batch_size = 1e5
    source.verbose_generator = True
    source.gpu_mode = (
        utility.get_gpu_mode_for_tests()
    )  # should be "auto" but "cpu" for macOS github actions to avoid mps errors

    # cuts (not need precision here)
    c = sim.physics_manager.global_production_cuts.all = 100 * mm

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test047.mhd"
    dose.attached_to = "ct"
    dose.size = [70, 70, 240]
    dose.spacing = [3.5 * mm, 3.5 * mm, 3.5 * mm]
    dose.output_coordinate_system = "attached_to_image"
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # ---------------------------------------------------------------
    # print results at the end
    print()
    gate.exception.warning("Tests stats file")
    print(stats)
    ref_stat_file = paths.output_ref / "t047_stats.txt"
    # stat.write(ref_stat_file) # (for reference)
    stats_ref = utility.read_stat_file(ref_stat_file)
    is_ok = utility.assert_stats(stats, stats_ref, 0.005)

    dose = sim.get_actor("dose")
    print()
    gate.exception.warning("Compare image to analog")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test047-edep.mhd",
            dose.get_output_path("edep"),
            stats,
            tolerance=19,
            ignore_value=0,
            axis="x",
        )
        and is_ok
    )

    print("Test with vv: ")
    print(f"vv {source.cond_image} --fusion {dose.get_output_path('edep')}")

    utility.test_ok(is_ok)
