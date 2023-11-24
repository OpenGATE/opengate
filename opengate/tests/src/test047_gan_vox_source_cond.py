#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__)

    """
    Data :
    gt_image_crop source_three_areas.mhd -o source_three_areas_crop.mhd
    gt_affine_transform -i source_three_areas_crop.mhd -o source_three_areas_crop_3.5mm.mhd  --newspacing 3.5 -fr -a -im NN
    """

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 1
    ui.random_seed = 123456789
    activity_bq = 1e6

    # visu
    if ui.visu:
        ui.number_of_threads = 1
        activity_bq = 100

    # add a material database
    sim.add_material_database(paths.data / "GateMaterials.db")

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
    if ui.visu:
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
    source.particle = "alpha"
    source.activity = activity_bq * Bq / ui.number_of_threads
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
        utility.get_gpu_mode()
    )  # should be "auto" but "cpu" for macOS github actions to avoid mps errors

    # cuts (not need precision here)
    c = sim.global_production_cuts.all = 100 * mm

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test047-edep.mhd"
    dose.mother = "ct"
    dose.size = [70, 70, 240]
    dose.spacing = [3.5 * mm, 3.5 * mm, 3.5 * mm]
    dose.img_coord_system = True
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    # output = sim.start(True)
    # FIXME
    sim.run()

    # ---------------------------------------------------------------
    # print results at the end
    print()
    gate.exception.warning("Tests stats file")
    stat = sim.output.get_actor("Stats")
    print(stat)
    ref_stat_file = paths.output_ref / "t047_stats.txt"
    # stat.write(ref_stat_file) # (for reference)
    stats_ref = utility.read_stat_file(ref_stat_file)
    is_ok = utility.assert_stats(stat, stats_ref, 0.005)

    print()
    gate.exception.warning("Compare image to analog")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test047-edep.mhd",
            dose.output,
            stat,
            tolerance=19,
            ignore_value=0,
            axis="x",
        )
        and is_ok
    )

    print("Test with vv: ")
    print(f"vv {source.cond_image} --fusion {dose.output}")

    utility.test_ok(is_ok)
