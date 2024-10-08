#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.geometry.materials import MaterialDatabase, assert_same_material
from opengate.tests import utility
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels", "test009")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.output_dir = paths.output

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    gcm3 = gate.g4_units.g_cm3

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]
    fake.rotation = Rotation.from_euler("x", -20, degrees=True).as_matrix()

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = paths.data / "patient-4mm.mhd"
    patient.mother = "fake"
    patient.material = "G4_AIR"  # material used by default
    f1 = str(paths.gate_data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.gate_data / "Schneider2000DensitiesTable.txt")
    tol = 0.05 * gcm3
    (
        patient.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    print(f"tol = {tol} g/cm3")
    print(f"mat : {len(patient.voxel_materials)} materials")
    patient.dump_label_image = paths.output / "test009_hu_label.mhd"
    # cuts
    patient.set_production_cut(particle_name="electron", value=3 * mm)

    # dump list of created material (for debug)
    fn = str(paths.output / "test009_materials.txt")
    with open(fn, "w") as file:
        file.write("[Materials]\n")
        for i, m in enumerate(materials):
            file.write(f"# {patient.voxel_materials[i]}\n")
            print(f"Build material number {i} named {m}")
            mat = sim.volume_manager.material_database.FindOrBuildMaterial(m)
            file.write(gate.geometry.materials.dump_material_like_Gate(mat))
    print("List of material in ", fn)

    # test material files
    gate.exception.warning(f"Check materials")
    db1 = MaterialDatabase()
    db1.read_from_file(str(paths.gate_data / "patient-HUmaterials.db"))
    db2 = MaterialDatabase()
    db2.read_from_file(fn)
    is_ok = True
    for m1 in db1.material_builders:
        m2 = db2.material_builders[m1]
        m1 = db1.material_builders[m1]
        t = assert_same_material(m1, m2)
        is_ok = utility.print_test(t, f"check {m1.name}") and is_ok

    # write the image of labels (None by default)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 130 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 10 * mm
    source.position.translation = [0, 0, -14 * cm]
    source.activity = 10000 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test009_hu.mhd"
    dose.attached_to = "patient"
    dose.size = [99, 99, 99]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.output_coordinate_system = "attached_to_image"
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = False

    # print info
    print(sim.volume_manager.dump_volumes())

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    gate.exception.warning(f"Check stats")
    print(stats)
    print(dose)

    # tests
    gate.exception.warning(f"Check dose")
    stats_ref = utility.read_stat_file(paths.gate_output / "stat_hu.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.15)
    is_ok = is_ok and utility.assert_images(
        paths.gate_output / "output_hu-Edep.mhd",
        dose.edep.get_output_path(),
        stats,
        tolerance=35,
    )

    utility.test_ok(is_ok)
