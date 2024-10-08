#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import itk
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
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

    # fake box
    b = sim.add_volume("Box", "fake1")
    b.size = [36 * cm, 36 * cm, 36 * cm]
    b.translation = [25 * cm, 0, 0]
    r = Rotation.from_euler("y", -25, degrees=True)
    r = r * Rotation.from_euler("x", -35, degrees=True)
    b.rotation = r.as_matrix()
    b = sim.add_volume("Box", "fake2")
    b.mother = "fake1"
    b.size = [35 * cm, 35 * cm, 35 * cm]

    # CT image #1
    ct_odd = sim.add_volume("Image", "ct_odd")
    ct_odd.image = paths.data / "10x10x10.mhd"
    ct_odd.mother = "fake2"
    ct_odd.voxel_materials = [[0, 10, "G4_WATER"]]
    ct_odd.translation = [-2 * cm, 0, 0]
    r = Rotation.from_euler("y", 25, degrees=True)
    r = r * Rotation.from_euler("x", 35, degrees=True)
    ct_odd.rotation = r.as_matrix()

    # CT image #2
    ct_even = sim.add_volume("Image", "ct_even")
    ct_even.image = paths.data / "11x11x11.mhd"
    ct_even.voxel_materials = [[0, 10, "G4_WATER"]]
    ct_even.voxel_materials = ct_odd.voxel_materials
    ct_even.translation = [-25 * cm, 0, 0]

    # source from sphere
    """
        WARNING : if the source is a point and is centered with odd image, the source
        is at the intersection of 3 planes (8 voxels): then, lot of "navigation warning"
        from G4 occur. Not really clear why.
        So we move the source a bit.
    """
    source = sim.add_source("GenericSource", "s_odd")
    source.particle = "alpha"
    source.activity = 1000 * Bq / sim.number_of_threads
    source.direction.type = "iso"
    source.mother = "ct_odd"
    source.position.translation = [10 * mm, 10 * mm, 10 * mm]
    source.energy.mono = 1 * MeV

    # source from sphere
    source = sim.add_source("GenericSource", "s_even")
    source.particle = "alpha"
    source.activity = 1000 * Bq / sim.number_of_threads
    source.direction.type = "iso"
    source.mother = "ct_even"
    source.position.translation = [0 * mm, 0 * mm, 0 * mm]
    source.energy.mono = 1 * MeV

    # source from spect
    source = sim.add_source("VoxelsSource", "vox")
    source.mother = "ct_even"
    source.particle = "alpha"
    source.activity = 1000 * Bq / sim.number_of_threads
    source.image = paths.data / "five_pixels.mha"
    source.direction.type = "iso"
    source.position.translation = [0 * mm, 0 * mm, 0 * mm]
    source.position.translation = gate.image.get_translation_between_images_center(
        str(ct_even.image), str(source.image)
    )
    source.energy.mono = 1 * MeV

    # cuts
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # add dose actor
    dose1 = sim.add_actor("DoseActor", "dose1")
    dose1.output = paths.output / "test021-odd-edep.mhd"
    dose1.mother = "ct_odd"
    img_info = gate.image.read_image_info(str(ct_odd.image))
    dose1.size = img_info.size
    dose1.spacing = img_info.spacing
    dose1.img_coord_system = True

    # add dose actor
    dose2 = sim.add_actor("DoseActor", "dose2")
    dose2.output = paths.output / "test021-even-edep.mhd"
    dose2.mother = "ct_even"
    img_info = gate.image.read_image_info(str(ct_even.image))
    dose2.size = img_info.size
    dose2.spacing = img_info.spacing
    dose2.translation = source.position.translation
    dose2.img_coord_system = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.get_actor("Stats")
    # stat.write('output_ref/stat021_ref.txt')

    # test pixels in dose #1
    dose1 = sim.get_actor("dose1")
    dose2 = sim.get_actor("dose2")
    d_odd = itk.imread(paths.output / dose1.user_info.output)
    s = itk.array_view_from_image(d_odd).sum()
    v = d_odd.GetPixel([5, 5, 5])
    diff = (s - v) / s
    tol = 0.01
    is_ok = diff < tol
    diff *= 100
    utility.print_test(is_ok, f"Image #1 (odd): {v:.2f} {s:.2f} -> {diff:.2f}%")

    # test pixels in dose #1
    d_even = itk.imread(paths.output / dose2.user_info.output)
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
        utility.print_test(b, f"Image #2 (even) {s:.2f} vs {v:.2f}  -> {p:.2f}%")
        return b

    is_ok = t(s, ss) and is_ok
    is_ok = t(1.80, v0) and is_ok
    is_ok = t(0.8, v1) and is_ok
    is_ok = t(0.8, v2) and is_ok
    is_ok = t(0.8, v3) and is_ok
    is_ok = t(0.8, v4) and is_ok

    stats_ref = utility.read_stat_file(paths.output_ref / "stat021_ref.txt")
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stat, stats_ref, 0.05) and is_ok

    utility.test_ok(is_ok)
