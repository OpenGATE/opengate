#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.image import get_translation_to_isocenter, resample_itk_image_like
from opengate.tests import utility
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.voxelize import (
    voxelize_geometry,
    write_voxelized_geometry,
    voxelized_source,
)
import itk
import json

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test015")

    # create the simulation
    sim = gate.Simulation()
    # sim.visu = True
    # sim.visu_type = "qt"
    sim.random_seed = 87456321
    sim.output_dir = paths.output
    sim.progress_bar = True

    # units
    MeV = gate.g4_units.MeV
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 10 * mm)

    # world size
    sim.world.size = [2 * m, 2 * m, 2 * m]

    # add an iec phantom
    iec = gate_iec.add_iec_phantom(sim)

    # add sources
    sources = []
    a = 100 * BqmL
    if sim.visu:
        a = 1 * BqmL
    s = gate_iec.add_central_cylinder_source(sim, iec.name, "s_cyl", a / 2)
    sources.append(s)
    s = gate_iec.add_spheres_sources(sim, iec.name, "s_sphere", "all", [a] * 6)
    for b in s:
        sources.append(b)
    s = gate_iec.add_background_source(sim, iec.name, "s_bg", a / 20)
    sources.append(s)

    total_activity = 0
    for s in sources:
        s.particle = "alpha"
        s.energy.type = "mono"
        s.energy.mono = 100 * MeV
        total_activity += s.activity
    print(f"Total activity: {total_activity/Bq} Bq")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = "test015_iec_phantom_5_stats.txt"

    # add dose actor
    dose1 = sim.add_actor("DoseActor", "dose1")
    dose1.edep.output_filename = "test015_iec_5_edep.mhd"
    dose1.attached_to = iec
    dose1.size = [150, 150, 150]
    dose1.spacing = [3 * mm, 3 * mm, 3 * mm]
    dose1.output_coordinate_system = "local"

    # voxelized iec
    spacing = (3.5 * mm, 2 * mm, 4.5 * mm)
    if sim.visu:
        spacing = (8 * mm, 8 * mm, 8 * mm)
    volume_labels, image = voxelize_geometry(sim, extent=iec, spacing=spacing, margin=1)
    filenames = write_voxelized_geometry(
        sim, volume_labels, image, paths.output / "test015_iec_5_geom.mhd"
    )
    print(filenames)

    # voxelize source
    a = 1
    activities = {
        "iec_sphere_10mm": a,
        "iec_sphere_13mm": a,
        "iec_sphere_17mm": a,
        "iec_sphere_22mm": a,
        "iec_sphere_28mm": a,
        "iec_sphere_37mm": a,
        "iec_interior": a / 20,
        "iec_center_cylinder_hole": a / 2,
    }

    img = itk.imread(filenames["image"])
    volume_labels = json.loads(open(filenames["volumes"]).read())
    img_source = voxelized_source(img, volume_labels, activities)
    itk.imwrite(img_source, paths.output / "test015_iec_5_geom_source.mhd")

    # add voxelized IEC
    # Warning: the position must be adapted for IEC (default position is center of the image)
    vox = sim.add_volume("ImageVolume", "iec_vox")
    vox.image = filenames["image"]
    vox.read_label_to_material(filenames["labels"])
    vox.translation = get_translation_to_isocenter(vox.image)
    # move on the left to avoid overlap
    vox.translation[0] -= 35 * cm

    # add source by reading vox
    source = sim.add_source("VoxelSource", "source")
    source.attached_to = vox
    source.image = paths.output / "test015_iec_5_geom_source.mhd"
    source.particle = "alpha"
    source.energy.type = "mono"
    source.energy.mono = 100 * MeV
    source.activity = total_activity

    # add another dose actor
    dose2 = sim.add_actor("DoseActor", "dose_vox")
    dose2.edep.output_filename = "test015_iec_5_edep_vox.mhd"
    dose2.attached_to = vox
    dose2.size = [150, 150, 150]
    dose2.spacing = [3 * mm, 3 * mm, 3 * mm]
    dose2.output_coordinate_system = "attached_to_image"

    # start
    sim.run()
    print(stats)

    # resample images in the same coordinate system
    img1 = itk.imread(dose1.edep.get_output_path())
    img2 = itk.imread(dose2.edep.get_output_path())
    img2_res = resample_itk_image_like(img2, img1, 0, linear=True)
    fn = str(dose2.edep.get_output_path()).replace(".mhd", "_resampled.mhd")
    itk.imwrite(img2_res, fn)

    # compare images
    is_ok = utility.assert_images(
        dose1.get_output_path("edep"),
        fn,
        stats=None,
        axis="y",
        tolerance=150,
        sum_tolerance=1.1,
        sad_profile_tolerance=4.0,
        ignore_value_data1=0,
        ignore_value_data2=0,
        # apply_ignore_mask_to_sum_check=False,  # force legacy behavior
    )

    utility.test_ok(is_ok)
