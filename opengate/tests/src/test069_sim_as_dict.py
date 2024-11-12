#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import pathlib

# This is just a dummy simulation to test the json archiving functionality
# It does not simulate any meaningful scenario

if __name__ == "__main__":
    pathFile = pathlib.Path(__file__).parent.resolve()
    paths = utility.get_default_test_paths(__file__)
    paths_test009 = utility.get_default_test_paths(__file__, "gate_test009_voxels")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False

    # store a json archive
    sim.store_json_archive = True
    sim.store_input_files = True
    sim.json_archive_filename = "simu_test069.json"
    sim.output_dir = paths.output / "test069"

    # add a material database
    sim.volume_manager.add_material_database(
        pathFile.parent / "data" / "GateMaterials.db"
    )

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    #  change world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # create a waterbox, but do not add it to the simulation
    waterbox = sim.volume_manager.create_volume("Box", "Waterbox")
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.material = "G4_WATER"

    # create and add a rod
    rod = sim.add_volume("Tubs", "rod")
    rod.rmax = 1 * cm
    rod.rmin = 0
    rod.dz = 6 * cm
    rod.mother = "world"
    rod.material = "G4_PLEXIGLASS"

    # "punch a hole" in the waterbox via boolean subtraction
    waterbox_with_hole = gate.geometry.volumes.subtract_volumes(
        waterbox, rod, new_name="waterbox_with_hole"
    )
    # and add the resulting volume
    sim.add_volume(waterbox_with_hole)

    # Note: the rod is higher (2 x 6 cm) than the waterbox so the rod sticks out of the punched-through waterbox

    # set production cuts in the rod volume
    sim.physics_manager.set_production_cut(
        volume_name=rod.name, value=1.78 * gate.g4_units.MeV, particle_name="proton"
    )

    # add an image volume
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "world"
    patient.translation = [0, 0, 30 * cm]
    patient.material = "G4_AIR"  # material used by default
    patient.voxel_materials = [
        [-2000, -900, "G4_AIR"],
        [-900, -100, "Lung"],
        [-100, 0, "G4_ADIPOSE_TISSUE_ICRP"],
        [0, 300, "G4_TISSUE_SOFT_ICRP"],
        [300, 800, "G4_B-100_BONE"],
        [800, 6000, "G4_BONE_COMPACT_ICRU"],
    ]

    stat_actor = sim.add_actor("SimulationStatisticsActor", name="stat_actor")

    # add a source so that this simulation can run
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 230 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 1 * mm
    source.position.translation = [0, 0, -80 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 10

    # run
    sim.run()

    # test the file content -> NO, there are some abs filenames ...
    fn1 = paths.output / "test069" / sim.json_archive_filename
    print(fn1)
    """fn2 = paths.output_ref / "test069" / sim.json_archive_filename
    f1 = open(fn1)
    j1 = json.load(f1)
    f2 = open(fn2)
    j2 = json.load(f2)
    is_ok = j1 == j2
    print(fn1)
    print(fn2)
    utility.print_test(is_ok, f"Compare json gate output with reference")"""
    is_ok = fn1.exists()

    utility.test_ok(is_ok)
