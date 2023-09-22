#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 1
    print(ui)

    # add a material database
    sim.add_material_database(paths.data / "GateMaterials.db")

    #  change world size
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    um = gate.g4_units.um
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    cm = gate.g4_units.cm
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_WATER"
    fake.color = [1, 0, 1, 1]
    fake.rotation = Rotation.from_euler("x", 2, degrees=True).as_matrix()

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "fake"
    patient.material = "G4_AIR"  # default material
    vm = gate.geometry.materials.read_voxel_materials(
        paths.gate_data / "patient-HU2mat-v1.txt"
    )
    vm[0][0] = -10000
    patient.voxel_materials = vm
    patient.dump_label_image = paths.output / "test020_labels.mhd"

    # activity
    activity = 100 * kBq

    # source 1
    source = sim.add_source("GenericSource", "source1")
    source.energy.mono = 150 * keV
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 10 * mm
    source.position.translation = [0, 0, -15 * cm]
    source.activity = activity / ui.number_of_threads
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # large cuts, no e- needed
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.global_production_cuts.gamma = 700 * um
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    sim.physics_manager.global_production_cuts.electron = 1 * m
    sim.physics_manager.global_production_cuts.proton = 1 * m

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test20-edep.mhd"
    dose.mother = "patient"
    dose.size = [100, 100, 100]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.img_coord_system = True  # default is True
    dose.translation = [0 * mm, 0 * mm, 1 * mm]

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")

    # start simulations
    sim.run()

    # print results at the end
    stat = sim.output.get_actor("Stats")
    print(stat)
    d = sim.output.get_actor("dose")
    print(d)

    # tests
    stats_ref = utility.read_stat_file(paths.gate / "output" / "stat_profiling.txt")
    stats_ref.counts.run_count = ui.number_of_threads
    is_ok = utility.assert_stats(stat, stats_ref, 0.1)
    is_ok = is_ok and utility.assert_images(
        paths.gate / "output" / "output_profiling-Edep.mhd",
        paths.output / "test20-edep.mhd",
        stat,
        tolerance=79,
    )
    utility.test_ok(is_ok)
