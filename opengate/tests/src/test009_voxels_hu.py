#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.geometry.materials import MaterialDatabase, assert_same_material
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

    # add a material database
    sim.add_material_database(paths.data / "GateMaterials.db")

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

    # dump list of created material (for debug)
    fn = str(paths.output / "test009_materials.txt")
    file = open(fn, "w")
    i = 0
    file.write("[Materials]\n")
    for m in materials:
        file.write(f"# {patient.voxel_materials[i]}\n")
        print("build", m)
        mat = sim.volume_manager.material_database.FindOrBuildMaterial(m)
        file.write(gate.geometry.materials.dump_material_like_Gate(mat))
        i = i + 1
    file.close()
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
    patient.dump_label_image = paths.output / "test009_hu_label.mhd"

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

    # cuts
    sim.set_production_cut(
        volume_name="patient",
        particle_name="electron",
        value=3 * mm,
    )

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output = paths.output / "test009_hu-edep.mhd"
    dose.mother = "patient"
    dose.size = [99, 99, 99]
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.img_coord_system = True
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = False

    # print info
    print(sim.dump_volumes())

    # verbose
    sim.apply_g4_command("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    gate.exception.warning(f"Check stats")
    stat = sim.output.get_actor("Stats")
    print(stat)
    d = sim.output.get_actor("dose")
    print(d)

    # tests
    gate.exception.warning(f"Check dose")
    stats_ref = utility.read_stat_file(paths.gate_output / "stat_hu.txt")
    is_ok = utility.assert_stats(stat, stats_ref, 0.15)
    is_ok = is_ok and utility.assert_images(
        paths.gate_output / "output_hu-Edep.mhd",
        paths.output / "test009_hu-edep.mhd",
        stat,
        tolerance=35,
    )

    utility.test_ok(is_ok)
