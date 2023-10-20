#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import opengate.contrib.spect.genm670 as gate_spect
import opengate as gate
import test043_garf_helpers as test43
from opengate.tests import utility

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.number_of_threads = 3
    ui.visu = False
    ui.random_seed = 321654987

    # units
    nm = gate.g4_units.nm
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    keV = gate.g4_units.keV

    # activity
    activity = 1e6 * Bq / ui.number_of_threads

    # add a material database
    sim.add_material_database(test43.paths.gate_data / "GateMaterials.db")

    # init world
    test43.sim_set_world(sim)

    # fake spect head
    head = gate_spect.add_ge_nm67_fake_spect_head(sim, "spect")
    head.translation = [0, 0, -15 * cm]

    # detector input plane (+ 1nm to avoid overlap)
    pos, crystal_dist, psd = gate_spect.get_plane_position_and_distance_to_crystal(
        "lehr"
    )
    pos += 1 * nm
    print(f"plane position     {pos / mm} mm")
    print(f"crystal distance   {crystal_dist / mm} mm")
    detPlane = test43.sim_add_detector_plane(sim, head.name, pos)

    # physics
    test43.sim_phys(sim)

    # sources
    test43.sim_source_test(sim, activity)

    # arf actor
    arf = sim.add_actor("ARFActor", "arf")
    arf.mother = detPlane.name
    arf.output = test43.paths.output / "test043_projection_garf_mt.mhd"
    arf.batch_size = 2e5
    arf.image_size = [128, 128]
    arf.image_spacing = [4.41806 * mm, 4.41806 * mm]
    arf.verbose_batch = True
    arf.distance_to_crystal = crystal_dist  # 74.625 * mm
    arf.distance_to_crystal = 74.625 * mm
    arf.pth_filename = test43.paths.gate_data / "pth" / "arf_Tc99m_v3.pth"
    arf.enable_hit_slice = True
    arf.gpu_mode = (
        utility.get_gpu_mode()
    )  # should be "auto" but "cpu" for macOS github actions to avoid mps errors

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("stats")
    print(stat)

    # print info
    print("")
    arf = sim.output.get_actor("arf")
    img = itk.imread(str(arf.user_info.output))
    # set the first channel to the same channel (spectrum) than the analog
    img[0, :] = img[1, :] + img[2, :]
    print(f"Number of batch: {arf.batch_nb}")
    print(f"Number of detected particles: {arf.detected_particles}")
    filename1 = str(arf.user_info.output).replace(".mhd", "_0.mhd")
    itk.imwrite(img, filename1)

    # high stat
    filename2 = str(arf.user_info.output).replace(".mhd", "_hs.mhd")
    scale = 4e8 * Bq / activity / ui.number_of_threads
    print(f"Scaling ref = 4e8, activity = {activity}, scale = {scale}")
    img2 = gate.image.scale_itk_image(img, scale)
    itk.imwrite(img2, filename2)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    print()
    gate.exception.warning("Tests stats file")
    stats_ref = utility.read_stat_file(test43.paths.gate_output / "stats_analog.txt")
    # dont compare steps of course
    stats_ref.counts.step_count = stat.counts.step_count
    stats_ref.counts.run_count = 3
    is_ok = utility.assert_stats(stat, stats_ref, 0.01)

    print()
    gate.exception.warning("Compare image to analog")
    is_ok = (
        utility.assert_images(
            test43.paths.output_ref / "test043_projection_analog.mhd",
            filename1,
            stat,
            tolerance=100,
            ignore_value=0,
            axis="x",
            sum_tolerance=20,
        )
        and is_ok
    )

    print()
    gate.exception.warning("Compare image to analog high statistics")
    is_ok = (
        utility.assert_images(
            test43.paths.output_ref / "test043_projection_analog_high_stat.mhd",
            filename2,
            stat,
            tolerance=52,
            ignore_value=0,
            axis="x",
        )
        and is_ok
    )

    print()
    gate.exception.warning("profile compare : ")
    p = test43.paths.output_ref
    print(
        f'garf_compare_image_profile {p / "test043_projection_analog.mhd"} {filename1} -w 3'
    )
    print(
        f'garf_compare_image_profile {p / "test043_projection_analog.mhd"} {filename1} -w 3 -s 75'
    )
    print(
        f'garf_compare_image_profile {p / "test043_projection_analog_high_stat.mhd"} {filename2} -w 3'
    )
    print(
        f'garf_compare_image_profile {p / "test043_projection_analog_high_stat.mhd"} {filename2} -w 3 -s 75'
    )

    utility.test_ok(is_ok)
