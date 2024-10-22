#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from matplotlib import pyplot as plt
from scipy.spatial.transform import Rotation

import opengate as gate
from opengate import g4_units
from opengate.tests import utility
from opengate.tests.src.test081_tle_helpers import add_waterbox, voxelize_waterbox
from opengate.tests.utility import get_image_1d_profile

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test081_tle")

    # create the simulation
    sim = gate.Simulation()

    # main options
    # sim.visu = True
    sim.visu_type = "qt"
    sim.random_seed = "auto"
    sim.output_dir = paths.output
    sim.progress_bar = True
    sim.number_of_threads = 4

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # create voxelized waterbox
    waterbox = add_waterbox(sim)
    # voxelize_waterbox(sim, paths.data / "test081_tle")

    # insert voxelized waterbox
    """spacing = 8
    waterbox = sim.add_volume("Image", "waterbox")
    fn = paths.data / "test081_tle" / f"waterbox_with_inserts_{spacing}mm_"
    waterbox.image = f"{fn}image.mhd"
    waterbox.set_materials_from_voxelisation(f"{fn}labels.json")
    """
    waterbox_size = [30 * cm, 30 * cm, 20 * cm]

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1 * mm
    sim.physics_manager.set_max_step_size("waterbox", 0.5 * mm)
    sim.physics_manager.set_user_limits_particles("gamma")

    # default source for tests
    source = sim.add_source("GenericSource", "source")
    source.energy.mono = 150 * keV
    source.particle = "gamma"
    source.position.type = "sphere"
    source.position.radius = 3 * cm
    source.position.translation = [0, 0, -55 * cm]
    source.direction.type = "focused"
    source.direction.focus_point = [0, 0, -20 * cm]
    source.n = 1e5 / sim.number_of_threads
    if sim.visu:
        source.n = 10

    # add conventional dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.output_filename = "test081.mhd"
    dose_actor.attached_to = waterbox
    dose_actor.dose_uncertainty.active = True
    dose_actor.dose.active = True
    dose_actor.size = [200, 200, 200]
    dose_actor.spacing = [x / y for x, y in zip(waterbox_size, dose_actor.size)]
    print(f"Dose actor pixels : {dose_actor.size}")
    print(f"Dose actor spacing : {dose_actor.spacing} mm")
    print(f"Dose actor size : {waterbox_size} mm")

    # add tle dose actor
    tle_dose_actor = sim.add_actor("TLEDoseActor", "tle_dose_actor")
    tle_dose_actor.output_filename = "test081_tle.mhd"
    tle_dose_actor.attached_to = waterbox
    tle_dose_actor.dose_uncertainty.active = True
    tle_dose_actor.dose.active = True
    tle_dose_actor.size = [200, 200, 200]  # dose_actor.size
    tle_dose_actor.spacing = [
        x / y for x, y in zip(waterbox_size, tle_dose_actor.size)
    ]  # dose_actor.spacing
    print(f"TLE Dose actor pixels : {tle_dose_actor.size}")
    print(f"TLE Dose actor spacing : {tle_dose_actor.spacing} mm")
    print(f"TLE Dose actor size : {waterbox_size} mm")

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run()

    # print results at the end
    print(stats)

    # plot pdd
    fig, ax = plt.subplots(ncols=2, nrows=1, figsize=(13, 5))

    a = ax[0]
    pdd_x, pdd_y = get_image_1d_profile(dose_actor.edep.get_output_path(), "z")
    a.plot(pdd_x, pdd_y, label="edep analog")
    pdd_x, pdd_y = get_image_1d_profile(tle_dose_actor.edep.get_output_path(), "z")
    a.plot(pdd_x, pdd_y, label="edep TLE")
    a.set_xlabel("distance [mm]")
    a.set_ylabel("edep [MeV]")
    a.legend()

    a = a.twinx()
    pdd_x, pdd_y = get_image_1d_profile(
        dose_actor.dose_uncertainty.get_output_path(), "z"
    )
    a.plot(
        pdd_x,
        pdd_y,
        label="uncert analog",
        linestyle="--",
        linewidth=0.5,
        color="lightseagreen",
    )
    pdd_x, pdd_y = get_image_1d_profile(
        tle_dose_actor.dose_uncertainty.get_output_path(), "z"
    )
    a.plot(
        pdd_x,
        pdd_y,
        label="uncert TLE",
        linestyle="--",
        linewidth=0.5,
        color="darkorange",
    )
    a.legend()

    a = ax[1]
    pdd_x, pdd_y = get_image_1d_profile(dose_actor.dose.get_output_path(), "z")
    a.plot(pdd_x, pdd_y, label="dose analog")
    pdd_x, pdd_y = get_image_1d_profile(tle_dose_actor.dose.get_output_path(), "z")
    a.plot(pdd_x, pdd_y, label="dose TLE")
    a.set_xlabel("distance [mm]")
    a.set_ylabel("dose [Gy]")
    a.legend()

    # output
    plt.savefig(paths.output / "pdd.png")
    plt.show()

    utility.test_ok(False)
