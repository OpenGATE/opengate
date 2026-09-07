#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
from opengate.geometry.materials import HounsfieldUnit_to_material
from opengate.image import get_translation_between_images_center, read_image_info
from opengate.logger import INFO
from opengate.managers import Simulation
from opengate.sources.utility import set_source_energy_spectrum
from opengate.utility import g4_best_unit, g4_units


def create_simulation(param):
    """
    param is dict with:
    - output_folder
    - visu
    - number_of_threads
    - ct_image
    - density_tolerance_gcm3
    - table_mat
    - table_density
    - verbose:
    - radionuclide
    - activity_bq
    """
    # create the simulation
    sim = Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = param.visu
    sim.visu_type = "vrml"
    sim.number_of_threads = param.number_of_threads
    sim.verbose_level = INFO
    param.output_folder = pathlib.Path(param.output_folder)
    sim.output_dir = param.output_folder
    sim.progress_bar = True

    # units
    m = g4_units.m
    mm = g4_units.mm
    keV = g4_units.keV
    Bq = g4_units.Bq
    gcm3 = g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # CT image
    if sim.visu:
        ct = sim.add_volume("Box", "ct")
        info = read_image_info(param.ct_image)
        ct.size = info.size
        ct.material = "G4_WATER"
        ct.color = [0, 0, 1, 1]
        sim.number_of_threads = 1
    else:
        ct = sim.add_volume("Image", "ct")
        ct.image = param.ct_image
        ct.material = "G4_AIR"  # material used by default
        tol = param.density_tolerance_gcm3 * gcm3
        ct.voxel_materials, materials = HounsfieldUnit_to_material(
            sim, tol, param.table_mat, param.table_density
        )
        if param.verbose:
            print(f'Density tolerance = {g4_best_unit(tol, "Volumic Mass")}')
            print(
                f"Number of materials in the CT : {len(ct.voxel_materials)} materials"
            )
        ct.dump_label_image = param.output_folder / "labels.mhd"

    # some radionuclides choice
    # (user of this function can still change
    # the source in the output sim)
    rad_list = {
        "Lu177": {"Z": 71, "A": 177, "name": "Lutetium 177"},
        "Y90": {"Z": 39, "A": 90, "name": "Yttrium 90"},
        "In111": {"Z": 49, "A": 111, "name": "Indium 111"},
        "I131": {"Z": 53, "A": 131, "name": "Iodine 131"},
    }

    # Activity source from an image
    source = sim.add_source("VoxelSource", "vox")
    source.attached_to = ct.name
    source.particle = "ion"
    source.ion.Z = rad_list[param.radionuclide]["Z"]
    source.ion.A = rad_list[param.radionuclide]["A"]
    source.activity = param.activity_bq * Bq
    source.image = param.activity_image
    source.direction.type = "iso"
    source.energy.mono = 0 * keV
    # compute the translation to align the source with CT
    # (considering they are in the same physical space)
    source.position.translation = get_translation_between_images_center(
        param.ct_image, param.activity_image
    )

    # cuts
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.set_production_cut("world", "all", 1 * m)
    sim.physics_manager.set_production_cut("ct", "all", 2 * mm)

    if not hasattr(param, "mode") or param.mode is None:
        param.mode = ""

    if param.mode == "e-":
        # electron source
        source.particle = "e-"
        set_source_energy_spectrum(source, param.radionuclide)
        sim.physics_manager.set_production_cut("ct", "all", 1 * m)
    elif "gamma" in param.mode:
        # gamma source
        source.particle = "gamma"
        set_source_energy_spectrum(source, param.radionuclide)
        sim.physics_manager.set_production_cut("ct", "all", 1 * m)

    # add dose actor (get the same size as the source)
    source_info = read_image_info(param.activity_image)
    if param.mode == "gamma_tle":
        dose = sim.add_actor("TLEDoseActor", "dose")
        dose.tle_threshold_type = "energy"
        dose.tle_threshold = source.energy.spectrum_energies[-1]
        print(f"tle_threshold = {dose.tle_threshold/keV} keV")
    else:
        dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "output.mhd"
    dose.dose_uncertainty.active = True
    dose.dose_squared.active = True
    dose.dose.active = True
    dose.attached_to = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    # set the origin of the dose like the source
    if not sim.visu:
        dose.output_coordinate_system = "attached_to_image"
    dose.hit_type = "random"
    dose.dose_uncertainty.active = True
    dose.dose_squared.active = True
    dose.dose.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True
    stats.output_filename = "stats.txt"
    stats.stats.write_to_disk = True

    return sim


def merge_vrt_dose_rate(folder_e, folder_gamma, output_folder, e_factor=1.0):
    """
    Merge the dose rate output images from electron and gamma simulations.
    Dose_total = e_factor * Dose_e + Dose_gamma
    """
    import itk
    import numpy as np
    import shutil

    folder_e = pathlib.Path(folder_e)
    folder_gamma = pathlib.Path(folder_gamma)
    output_folder = pathlib.Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    merged_files = []
    # Determine filename prefix: prefer 'output', fallback to 'edep'
    prefix = "output"
    if (
        not (folder_e / "output_edep.mhd").exists()
        and (folder_e / "edep_edep.mhd").exists()
    ):
        prefix = "edep"

    # Merge edep and dose images
    for suffix in ["edep.mhd", "dose.mhd"]:
        image_name = f"{prefix}_{suffix}"
        path_e = folder_e / image_name
        path_gamma = folder_gamma / image_name
        if path_e.exists() and path_gamma.exists():
            img_e = itk.imread(str(path_e))
            img_gamma = itk.imread(str(path_gamma))
            arr_e = itk.GetArrayFromImage(img_e)
            arr_gamma = itk.GetArrayFromImage(img_gamma)

            arr_total = float(e_factor) * arr_e + arr_gamma
            img_total = itk.GetImageFromArray(arr_total)
            img_total.CopyInformation(img_e)

            out_path = output_folder / f"output_{suffix}"
            itk.imwrite(img_total, str(out_path))
            merged_files.append(out_path)

    # Merge relative uncertainty if available
    unc_name = f"{prefix}_dose_uncertainty.mhd"
    dose_name = f"{prefix}_dose.mhd"
    unc_e_path = folder_e / unc_name
    unc_gamma_path = folder_gamma / unc_name
    dose_e_path = folder_e / dose_name
    dose_gamma_path = folder_gamma / dose_name

    if (
        unc_e_path.exists()
        and unc_gamma_path.exists()
        and dose_e_path.exists()
        and dose_gamma_path.exists()
    ):
        arr_unc_e = itk.GetArrayFromImage(itk.imread(str(unc_e_path)))
        arr_unc_gamma = itk.GetArrayFromImage(itk.imread(str(unc_gamma_path)))
        arr_dose_e = itk.GetArrayFromImage(itk.imread(str(dose_e_path)))
        arr_dose_gamma = itk.GetArrayFromImage(itk.imread(str(dose_gamma_path)))

        arr_dose_total = float(e_factor) * arr_dose_e + arr_dose_gamma
        # Absolute variance: (F * unc_e * dose_e)^2 + (unc_gamma * dose_gamma)^2
        abs_var = (float(e_factor) * arr_unc_e * arr_dose_e) ** 2 + (
            arr_unc_gamma * arr_dose_gamma
        ) ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            arr_unc_total = np.where(
                arr_dose_total > 0, np.sqrt(abs_var) / arr_dose_total, 0.0
            )

        img_unc_total = itk.GetImageFromArray(arr_unc_total.astype(np.float32))
        img_unc_total.CopyInformation(itk.imread(str(unc_e_path)))
        out_unc_path = output_folder / "output_dose_uncertainty.mhd"
        itk.imwrite(img_unc_total, str(out_unc_path))
        merged_files.append(out_unc_path)

    # Copy labels from electron run if present
    for label_file in ["labels.mhd", "labels.raw", "labels.json"]:
        src = folder_e / label_file
        if src.exists():
            shutil.copy2(src, output_folder / label_file)

    return merged_files
