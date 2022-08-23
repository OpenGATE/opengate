#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib

import opengate as gate


def dose_rate(param):
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = param.visu
    ui.number_of_threads = param.number_of_threads
    ui.verbose_level = gate.INFO

    param.output_folder = pathlib.Path(param.output_folder)

    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    keV = gate.g4_units("keV")
    Bq = gate.g4_units("Bq")
    gcm3 = gate.g4_units("g/cm3")

    #  change world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # CT image
    ct = sim.add_volume("Image", "ct")
    ct.image = param.ct_image
    ct.material = "G4_AIR"  # material used by default
    tol = param.density_tolerance_gcm3 * gcm3
    ct.voxel_materials, materials = gate.HounsfieldUnit_to_material(
        tol, param.table_mat, param.table_density
    )
    if param.verbose:
        print(f'Density tolerance = {gate.g4_best_unit(tol, "Volumic Mass")}')
        print(f"Number of materials in the CT : {len(ct.voxel_materials)} materials")
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
    source = sim.add_source("Voxels", "vox")
    source.mother = ct.name
    source.particle = "ion"
    source.ion.Z = rad_list[param.radionuclide]["Z"]
    source.ion.A = rad_list[param.radionuclide]["A"]
    source.activity = param.activity_bq * Bq / ui.number_of_threads
    source.image = param.activity_image
    source.direction.type = "iso"
    source.energy.mono = 0 * keV
    # compute the translation to align the source with CT
    # (considering they are in the same physical space)
    source.position.translation = gate.get_translation_between_images_center(
        param.ct_image, param.activity_image
    )

    # cuts
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    p.enable_decay = True  # FIXME
    sim.set_cut("world", "all", 1 * m)
    sim.set_cut("ct", "all", 1 * mm)

    # add dose actor (get the same size as the source)
    source_info = gate.read_image_info(param.activity_image)
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = param.output_folder / "edep.mhd"
    dose.mother = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    # set the origin of the dose like the source
    dose.img_coord_system = True
    dose.hit_type = "random"
    dose.uncertainty = False

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    return sim
