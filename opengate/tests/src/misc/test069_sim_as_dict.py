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

    # store a json archive explicitly
    archive_filename = "simu_test069.json"
    sim.output_dir = paths.output / "test069"

    # add a material database
    sim.volume_manager.add_material_database(
        pathFile.parent.parent / "data" / "GateMaterials.db"
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
    sim.to_json_file(filename=archive_filename)
    sim.archive_input_files()

    # test the file content
    fn1 = paths.output / "test069" / archive_filename
    print(fn1)

    from opengate.serialization import load_json

    with open(fn1) as f:
        dct = load_json(f)

    is_ok = "source_manager" in dct
    if is_ok:
        sources_dct = dct["source_manager"]["sources"]
        is_ok = is_ok and ("mysource" in sources_dct)
        if "mysource" in sources_dct:
            mysource_dct = sources_dct["mysource"]
            is_ok = is_ok and (mysource_dct["user_info"]["particle"] == "proton")
            is_ok = is_ok and (mysource_dct["user_info"]["energy"]["mono"] == 230 * MeV)

    # Test reading back
    sim2 = gate.Simulation()
    sim2.from_dictionary(dct)
    is_ok = is_ok and (sim2.source_manager.get_source("mysource").particle == "proton")
    is_ok = is_ok and (
        sim2.source_manager.get_source("mysource").energy.mono == 230 * MeV
    )

    is_ok = is_ok and fn1.exists()
    utility.test_ok(is_ok)
