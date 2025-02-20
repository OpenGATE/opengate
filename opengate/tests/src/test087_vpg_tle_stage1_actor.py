#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from vtkmodules.vtkFiltersModeling import vtkGeodesicPath

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test087_vpg_tle")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = "auto"  # FIXME to be replaced by a fixed number at the end
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.number_of_threads = 1

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    gcm3 = gate.g4_units.g_cm3
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # insert voxelized CT
    ct = sim.add_volume("Image", "ct")
    ct.image = paths.data / f"ct_4mm.mhd"
    if sim.visu:
        ct.image = paths.data / f"ct_40mm.mhd"
    ct.material = "G4_AIR"
    f1 = str(paths.data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.data / "Schneider2000DensitiesTable.txt")
    tol = 0.05 * gcm3
    (
        ct.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    print(f"tol = {tol/gcm3} g/cm3")
    print(f"mat : {len(ct.voxel_materials)} materials")
    ct.dump_label_image = paths.output / "labels.mhd"

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # source of proton
    # FIXME to replace by a more realistic proton beam, see tests 044
    source = sim.add_source("GenericSource", "proton_beam")
    source.energy.mono = 130 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 10 * mm
    source.position.translation = [0, -44 * cm, 0]
    source.activity = 10000 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]

    # add vpgtle actor
    vpg_tle = sim.add_actor("VoxelizedPromptGammaTLEActor", "vpgtle")
    vpg_tle.attached_to = ct
    vpg_tle.output_filename = "vpgtle.nii.gz"
    vpg_tle.size = [100, 100, 100]
    vpg_tle.bins = 50
    vpg_tle.spacing = [2 * mm, 2 * mm, 2 * mm]
    # FIXME to put elsewhere ? change the name ?
    vpg_tle.stage_0_database = paths.data / "vpgtle_stage0.db"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # FIXME to a real test
    is_ok = False
    utility.test_ok(is_ok)
