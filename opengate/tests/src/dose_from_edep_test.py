#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from scipy.spatial.transform import Rotation
import itk
import numpy as np

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels", "test041")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # # waterbox
    # patient = sim.add_volume("Box", "patient")
    # patient.size = [252,252,220]
    # patient.material = "G4_WATER"
    # patient.color = [0, 0, 1, 1]

    # image volume
    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]
    # fake.rotation = Rotation.from_euler("x", -20, degrees=True).as_matrix()

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
    print(f"tol = {tol/gcm3} g/cm3")
    print(f"mat : {len(patient.voxel_materials)} materials")
    patient.dump_label_image = paths.output / "test009_hu_label.mhd"
    # cuts
    patient.set_production_cut(particle_name="electron", value=3 * mm)

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BERT_EMV"
    sim.physics_manager.global_production_cuts.all = 1 * mm

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 115 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, -300 * mm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 5000 * Bq

    # add dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    # let the actor score other quantities additional to edep (default)
    dose_actor.edep_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.density.active = True
    dose_actor.score_in = "material"
    # set the filename once for the actor
    # a suffix will be added automatically for each output,
    # i.e. _edep, _edep_uncertainty, _dose
    dose_actor.output_filename = "test041.mhd"
    dose_actor.attached_to = patient
    dose_actor.size = [63, 63, 55]
    dose_actor.output_coordinate_system = "attached_to_image"
    mm = gate.g4_units.mm
    ts = [252 * mm, 252 * mm, 220 * mm]
    dose_actor.spacing = [x / y for x, y in zip(ts, dose_actor.size)]
    print(dose_actor.spacing)
    dose_actor.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stats)

    # compare dose image vs dose obtained as edep / mass at end of simulation
    dose_from_edep = dose_actor.compute_dose_from_edep_img()
    dose_from_edep.write(paths.output / "dose_from_edep.mhd")

    # test density calculated from CT values
    density_ct = dose_actor.create_density_image_from_image_volume(
        dose_actor.dose.image
    )
    itk.imwrite(density_ct, paths.output / "density_ct.mhd")

    gate.exception.warning("\nDifference for density in g/cm3")
    is_ok = utility.assert_images(
        paths.output / "density_ct.mhd",
        dose_actor.density.get_output_path(),
        stats,
        tolerance=10,
        ignore_value_data2=0,
    )

    gate.exception.warning("\nDifference for dose in Gray")
    is_ok = utility.assert_images(
        paths.output / "dose_from_edep.mhd",
        dose_actor.dose.get_output_path(),
        stats,
        tolerance=10,
        ignore_value_data2=0,
    )

    utility.test_ok(is_ok)
