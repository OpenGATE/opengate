#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib
from opengate.managers import Simulation
from opengate.utility import g4_units, g4_best_unit
from opengate.image import get_translation_between_images_center, read_image_info
from opengate.logger import INFO
from opengate.geometry.materials import HounsfieldUnit_to_material


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
    source = sim.add_source("VoxelsSource", "vox")
    source.mother = ct.name
    source.particle = "ion"
    source.ion.Z = rad_list[param.radionuclide]["Z"]
    source.ion.A = rad_list[param.radionuclide]["A"]
    source.activity = param.activity_bq * Bq / sim.number_of_threads
    source.image = param.activity_image
    source.direction.type = "iso"
    source.energy.mono = 0 * keV
    # compute the translation to align the source with CT
    # (considering they are in the same physical space)
    source.position.translation = get_translation_between_images_center(
        param.ct_image, param.activity_image
    )

    # cuts
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = True
    sim.physics_manager.set_production_cut("world", "all", 1 * m)
    sim.physics_manager.set_production_cut("ct", "all", 1 * mm)

    # add dose actor (get the same size as the source)
    source_info = read_image_info(param.activity_image)
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "edep.mhd"
    dose.attached_to = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    # set the origin of the dose like the source
    if not sim.visu:
        dose.output_coordinate_system = "attached_to_image"
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    return sim
