#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np

import opengate as gate
from opengate.actors.dynamicactors import SourceActivityImageChanger
from opengate.tests import utility


def create_activity_image(reference_image, peak_weights, output_path):
    array = np.zeros_like(itk.array_view_from_image(reference_image), dtype=np.float32)
    for peak_index, weight in peak_weights.items():
        array[peak_index] = weight
    image = itk.image_from_array(array)
    image.CopyInformation(reference_image)
    itk.imwrite(image, str(output_path))
    return image


def create_reference_image(output_path):
    array = np.zeros((10, 10, 10), dtype=np.float32)
    image = itk.image_from_array(array)
    image.SetSpacing([1.0, 1.0, 1.0])
    image.SetOrigin([0.0, 0.0, 0.0])
    itk.imwrite(image, str(output_path))
    return image


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test097")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 1
    sim.random_seed = 123456
    sim.output_dir = paths.output

    m = gate.g4_units.m
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    sec = gate.g4_units.s

    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")
    sim.world.size = [1 * m, 1 * m, 1 * m]

    ct_image_path = paths.output / "ct_image.mhd"
    ct_itk = create_reference_image(ct_image_path)

    ct = sim.add_volume("Image", "ct")
    ct.image = str(ct_image_path)
    ct.material = "G4_AIR"
    ct.voxel_materials = [[0, 10, "G4_WATER"]]

    ct_info = gate.image.read_image_info(ct.image)

    source_image_1_path = paths.output / "dynamic_source_1.mhd"
    source_image_2_path = paths.output / "dynamic_source_2.mhd"
    run_0_primary_peak = (5, 5, 2)
    run_0_secondary_peak = (5, 2, 2)
    run_1_primary_peak = (5, 5, 7)
    run_1_secondary_peak = (5, 2, 7)
    run_0_expected_ratio = 3.0
    run_1_expected_ratio = 4.0
    create_activity_image(
        ct_itk,
        {
            run_0_primary_peak: run_0_expected_ratio,
            run_0_secondary_peak: 1.0,
        },
        source_image_1_path,
    )
    create_activity_image(
        ct_itk,
        {
            run_1_primary_peak: run_1_expected_ratio,
            run_1_secondary_peak: 1.0,
        },
        source_image_2_path,
    )

    source = sim.add_source("VoxelSource", "vox_source")
    source.attached_to = ct.name
    source.particle = "alpha"
    source.n = [2000, 2000]
    source.image = str(source_image_1_path)
    source.direction.type = "iso"
    source.position.translation = gate.image.get_translation_between_images_center(
        ct.image, source_image_1_path
    )
    source.energy.mono = 1 * MeV
    source.add_dynamic_parametrisation(
        image=[source_image_1_path, source_image_2_path]
    )

    changer = SourceActivityImageChanger(
        name="source_activity_image_changer",
        activity_images=[source_image_1_path, source_image_2_path],
        attached_to=source,
        simulation=sim,
    )

    dose = sim.add_actor("DoseActor", "dose")
    dose.attached_to = ct.name
    dose.size = ct_info.size
    dose.spacing = ct_info.spacing
    dose.output_coordinate_system = "attached_to_image"
    dose.edep.keep_data_per_run = True

    sim.add_actor("SimulationStatisticsActor", "stats")

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.run_timing_intervals = [(0, 0.5 * sec), (0.5 * sec, 1 * sec)]

    sim.run()

    run_0 = itk.array_view_from_image(dose.edep.get_data(which=0))
    run_1 = itk.array_view_from_image(dose.edep.get_data(which=1))
    run_0_peak = np.unravel_index(np.argmax(run_0), run_0.shape)
    run_1_peak = np.unravel_index(np.argmax(run_1), run_1.shape)
    run_0_primary_dose = run_0[run_0_primary_peak]
    run_0_secondary_dose = run_0[run_0_secondary_peak]
    run_1_primary_dose = run_1[run_1_primary_peak]
    run_1_secondary_dose = run_1[run_1_secondary_peak]
    run_0_ratio = run_0_primary_dose / run_0_secondary_dose
    run_1_ratio = run_1_primary_dose / run_1_secondary_dose
    ratio_tolerance = 0.6

    is_ok = True
    utility.print_test(
        changer.attached_to == source.name,
        f"Changer attached_to property resolves to source name: {changer.attached_to}",
    )
    is_ok = changer.attached_to == source.name and is_ok

    utility.print_test(
        run_0_peak == run_0_primary_peak,
        f"Run 0 peak at {run_0_peak}, expected {run_0_primary_peak}",
    )
    is_ok = run_0_peak == run_0_primary_peak and is_ok

    utility.print_test(
        run_1_peak == run_1_primary_peak,
        f"Run 1 peak at {run_1_peak}, expected {run_1_primary_peak}",
    )
    is_ok = run_1_peak == run_1_primary_peak and is_ok

    utility.print_test(
        abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance,
        f"Run 0 dose ratio {run_0_ratio:.2f}, expected {run_0_expected_ratio:.2f}",
    )
    is_ok = abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance and is_ok

    utility.print_test(
        abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance,
        f"Run 1 dose ratio {run_1_ratio:.2f}, expected {run_1_expected_ratio:.2f}",
    )
    is_ok = abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance and is_ok

    utility.test_ok(is_ok)
