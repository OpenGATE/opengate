#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import numpy as np
import matplotlib.pyplot as plt
import opengate as gate
from opengate.geometry.materials import MaterialDatabase, assert_same_material
from opengate.tests import utility
import pathlib
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test009_voxels")

    path_to_4d_ct = paths.data / "test070" / "4d_ct"

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.output_dir = paths.output / "test070"

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    mm = gate.g4_units.mm
    gcm3 = gate.g4_units.g_cm3
    sec = gate.g4_units.second

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # image
    patient = sim.add_volume("Image", "patient")
    patient.image = path_to_4d_ct / "0.0.mhd"
    patient.read_input_image()
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
    # cuts
    patient.set_production_cut(particle_name="electron", value=3 * mm)

    # create time intervals to sample a cosine dynamics
    times_cos_first_half = np.arccos(np.linspace(1, -1, 6))[:-1]
    times_cos_second_half = np.pi * 2 - np.arccos(np.linspace(-1, 1, 6))
    times_cos = np.concatenate((times_cos_first_half, times_cos_second_half))
    # normalize tp [0, 1) interval
    times_cos /= 2 * np.pi
    interval_lengths = np.diff(times_cos)

    print(f"times_cos: {times_cos}")
    print(f"interval_lengths: {interval_lengths}")

    # set the run timing intervals
    sim.run_timing_intervals = [
        (t * sec, (t + l) * sec) for t, l in zip(times_cos[:-1], interval_lengths)
    ]

    # set the list of images as dynamic parametrisation
    paths_4d_ct = [path_to_4d_ct / f"{10*i}.0.mhd" for i in range(10)]
    patient.add_dynamic_parametrisation(image=paths_4d_ct)

    # check time samples:
    # y = np.concatenate((np.linspace(1, -1, 6)[:-1], np.linspace(-1, 1, 6)))
    # plt.figure()
    # plt.scatter(times_cos, y)

    # default source for tests
    source = sim.add_source("GenericSource", "proton_source")
    source.energy.mono = 100 * MeV
    source.particle = "proton"
    source.position.type = "sphere"
    source.position.radius = 10 * mm
    source.position.translation = [40 * cm, 0, 0 * cm]
    # source.n = 10000
    source.activity = 10000 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test070.mhd"
    dose.attached_to = "patient"
    dose.size = patient.size_pix
    dose.spacing = patient.spacing
    dose.output_coordinate_system = "attached_to_image"
    # dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.hit_type = "random"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = False

    # print info
    sim.volume_manager.print_volumes()

    # verbose
    sim.g4_commands_after_init.append("/tracking/verbose 0")

    # start simulation
    sim.run()

    # print results at the end
    gate.exception.warning(f"Check stats")
    print(stats)
    print(dose)
