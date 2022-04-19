#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pathlib

import gam_gate as gam


def dose_rate(param):
    # create the simulation
    sim = gam.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = param.visu
    ui.number_of_threads = param.number_of_threads
    ui.verbose_level = gam.DEBUG
    print(ui)

    param.output_folder = pathlib.Path(param.output_folder)

    # units
    m = gam.g4_units('m')
    mm = gam.g4_units('mm')
    keV = gam.g4_units('keV')
    Bq = gam.g4_units('Bq')

    #  change world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # CT image
    ct = sim.add_volume('Image', 'ct')
    ct.image = param.ct_image
    ct.material = 'G4_AIR'  # material used by default
    ct.voxel_materials = [[-2000, -900, 'G4_AIR'],
                          [-900, -100, 'G4_LUNG_ICRP'],
                          [-100, 0, 'G4_ADIPOSE_TISSUE_ICRP'],
                          [0, 300, 'G4_TISSUE_SOFT_ICRP'],
                          [300, 800, 'G4_B-100_BONE'],
                          [800, 6000, 'G4_BONE_COMPACT_ICRU']]
    ct.voxel_materials = [[-2000, 3000, 'G4_AIR']]
    ct.dump_label_image = param.output_folder / 'labels.mhd'

    # Activity source from an image
    source = sim.add_source('Voxels', 'vox')
    source.mother = ct.name
    source.img_coord_system = True
    source.particle = 'ion'
    source.ion.Z = 71
    source.ion.A = 177
    source.activity = param.activity_bq * Bq / ui.number_of_threads
    source.image = param.activity_image
    source.direction.type = 'iso'
    source.energy.mono = 0 * keV
    # compute the translation to align the source with CT
    # (considering they are in the same physical space)
    source.position.translation = gam.get_translation_between_images_center(param.ct_image, param.activity_image)

    # cuts
    p = sim.get_physics_user_info()
    p.physics_list_name = 'G4EmStandardPhysics_option4'
    p.enable_decay = True  # FIXME
    sim.set_cut('world', 'all', 1 * m)
    sim.set_cut('ct', 'all', 1 * mm)

    # add dose actor (get the same size as the source)
    source_info = gam.read_image_info(param.activity_image)
    dose = sim.add_actor('DoseActor', 'dose')
    dose.save = param.output_folder / 'edep.mhd'
    dose.mother = ct.name
    dose.size = source_info.size
    dose.spacing = source_info.spacing
    # translate the dose the same way as the source
    dose.translation = source.position.translation
    # set the origin of the dose like the source
    # dose.output_origin = source_info.origin
    dose.img_coord_system = True
    dose.hit_type = 'random'
    dose.uncertainty = False

    # add stat actor
    stats = sim.add_actor('SimulationStatisticsActor', 'Stats')
    stats.track_types_flag = True

    # create G4 objects
    sim.initialize()

    # start simulation
    sim.start()

    # print results at the end
    stats = sim.get_actor('Stats')
    print(stats)
    stats.write(param.output_folder / 'stats.txt')
