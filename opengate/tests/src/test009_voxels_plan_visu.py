#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.geometry.materials import (
    read_voxel_materials,
)
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels", "test009")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.output_dir = paths.output / __file__.rstrip(".py")
    sim.g4_verbose = True
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.store_json_archive = True
    sim.json_archive_filename = "simulation_test009_voxels.json"

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    deg = gate.g4_units.deg

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]
    # fake.rotation = Rotation.from_euler("x", 20, degrees=True).as_matrix()

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "source_test.mhd"
    patient.mother = "fake"
    patient.material = "G4_AIR"  # material used by default
    patient.color = [1, 0, 1, 1]
    patient.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]
    # or alternatively, from a file (like in Gate)
    vm = read_voxel_materials(paths.gate_data / "patient-HU2mat-v1.txt")
    vm[0][0] = -2000
    # Note: the voxel_materials are turned into a structured array when setting the user info
    # Therefore, we store the previous one, assign the new one, and only then compare them!
    assert patient.voxel_materials == vm
    patient.voxel_materials = vm
    # write the image of labels (None by default)
    patient.dump_label_image = paths.output / "test009_label.mhd"

    # default source for tests
    source = sim.add_source("VoxelSource", "mysource")

    source.particle = "proton"
    source.activity = 10 * Bq
    source.image = paths.data / "source_test.mhd"
    source.direction.type = "iso"
    source.direction.theta = [10 * deg, 10 * deg]
    source.direction.phi = [80 * deg, 90 * deg]
    source.energy.mono = 130 * MeV
    source.attached_to = "patient"

    # cuts
    patient.set_production_cut(
        particle_name="electron",
        value=3 * mm,
    )

    # add dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.attached_to = "patient"
    dose_actor.edep_uncertainty.active = True
    dose_actor.size = [99, 99, 99]
    dose_actor.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose_actor.output_coordinate_system = "attached_to_image"
    dose_actor.translation = [2 * mm, 3 * mm, -2 * mm]
    dose_actor.hit_type = "random"

    # add stat actor
    stats_actor = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats_actor.track_types_flag = True

    # print info
    print(sim.volume_manager.dump_volumes())

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    print(stats_actor)
    print(dose_actor)

    utility.test_ok(True)
