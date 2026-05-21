#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import matplotlib.pyplot as plt
import numpy as np

import opengate as gate
from opengate.actors.dynamicactors import SourceActivityImageChanger
from opengate.tests import utility


def xyz_to_zyx(index_xyz):
    return tuple(reversed(index_xyz))


def create_activity_image(reference_image, peak_weights, output_path):
    array = np.zeros_like(itk.array_view_from_image(reference_image), dtype=np.float32)
    for peak_index_xyz, weight in peak_weights.items():
        array[xyz_to_zyx(peak_index_xyz)] = weight
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


def plot_run_dose_planes(run_0_image, run_1_image, output_path):
    run_0_array = itk.array_view_from_image(run_0_image)
    run_1_array = itk.array_view_from_image(run_1_image)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    plane_index = 5
    images = [
        axes[0].imshow(run_0_array[plane_index, :, :], origin="lower"),
        axes[1].imshow(run_1_array[plane_index, :, :], origin="lower"),
    ]
    titles = ["Run 0 dose, z=5", "Run 1 dose, z=5"]

    for ax, image, title in zip(axes, images, titles):
        ax.set_title(title)
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
        fig.colorbar(image, ax=ax)

    fig.savefig(output_path)
    plt.close(fig)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test097_mt")

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 2
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
    ct.load_input_image()
    ct_info = gate.image.read_image_info(ct.image)

    source_image_1_path = paths.output / "dynamic_source_1.mhd"
    source_image_2_path = paths.output / "dynamic_source_2.mhd"
    run_0_primary_peak_xyz = (2, 5, 5)
    run_0_secondary_peak_xyz = (2, 2, 5)
    run_1_primary_peak_xyz = (7, 5, 5)
    run_1_secondary_peak_xyz = (7, 2, 5)
    run_0_expected_ratio = 3.0
    run_1_expected_ratio = 4.0
    create_activity_image(
        ct_itk,
        {
            run_0_primary_peak_xyz: run_0_expected_ratio,
            run_0_secondary_peak_xyz: 1.0,
        },
        source_image_1_path,
    )
    create_activity_image(
        ct_itk,
        {
            run_1_primary_peak_xyz: run_1_expected_ratio,
            run_1_secondary_peak_xyz: 1.0,
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
    source.add_dynamic_parametrisation(image=[source_image_1_path, source_image_2_path])

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

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.physics_manager.physics_list_name = "QGSP_BERT_EMZ"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.run_timing_intervals = [(0, 0.5 * sec), (0.5 * sec, 1 * sec)]

    sim.run()

    run_0_image = dose.edep.get_data(which=0)
    run_1_image = dose.edep.get_data(which=1)
    plot_run_dose_planes(
        run_0_image,
        run_1_image,
        paths.output / "test097_dynamic_voxel_source_mt_dose_planes.png",
    )
    run_0_primary_dose = run_0_image.GetPixel(run_0_primary_peak_xyz)
    run_0_secondary_dose = run_0_image.GetPixel(run_0_secondary_peak_xyz)
    run_1_primary_dose = run_1_image.GetPixel(run_1_primary_peak_xyz)
    run_1_secondary_dose = run_1_image.GetPixel(run_1_secondary_peak_xyz)
    run_0_other_primary_dose = run_0_image.GetPixel(run_1_primary_peak_xyz)
    run_1_other_primary_dose = run_1_image.GetPixel(run_0_primary_peak_xyz)
    run_0_ratio = run_0_primary_dose / run_0_secondary_dose
    run_1_ratio = run_1_primary_dose / run_1_secondary_dose
    ratio_tolerance = 0.8

    is_ok = True
    utility.print_test(
        changer.attached_to == source.name,
        f"Changer attached_to property resolves to source name: {changer.attached_to}",
    )
    is_ok = changer.attached_to == source.name and is_ok

    utility.print_test(
        stats.counts.runs == sim.number_of_threads * len(sim.run_timing_intervals),
        f"Stats runs count {stats.counts.runs} matches threads x timing intervals",
    )
    is_ok = (
        stats.counts.runs == sim.number_of_threads * len(sim.run_timing_intervals)
        and is_ok
    )

    utility.print_test(
        run_0_primary_dose > 5.0 * run_0_other_primary_dose,
        f"Run 0 primary voxel dose {run_0_primary_dose:.2f} dominates inactive run 1 voxel {run_0_other_primary_dose:.2f}",
    )
    is_ok = run_0_primary_dose > 5.0 * run_0_other_primary_dose and is_ok

    utility.print_test(
        run_1_primary_dose > 5.0 * run_1_other_primary_dose,
        f"Run 1 primary voxel dose {run_1_primary_dose:.2f} dominates inactive run 0 voxel {run_1_other_primary_dose:.2f}",
    )
    is_ok = run_1_primary_dose > 5.0 * run_1_other_primary_dose and is_ok

    utility.print_test(
        abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance,
        f"Run 0 dose ratio at xyz {run_0_primary_peak_xyz}/{run_0_secondary_peak_xyz}: {run_0_ratio:.2f}, expected {run_0_expected_ratio:.2f}",
    )
    is_ok = abs(run_0_ratio - run_0_expected_ratio) < ratio_tolerance and is_ok

    utility.print_test(
        abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance,
        f"Run 1 dose ratio at xyz {run_1_primary_peak_xyz}/{run_1_secondary_peak_xyz}: {run_1_ratio:.2f}, expected {run_1_expected_ratio:.2f}",
    )
    is_ok = abs(run_1_ratio - run_1_expected_ratio) < ratio_tolerance and is_ok

    utility.test_ok(is_ok)
