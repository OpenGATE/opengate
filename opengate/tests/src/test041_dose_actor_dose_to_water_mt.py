#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
import matplotlib.pyplot as plt
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test041_dose_actor_dose_to_water", "test041"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123456
    sim.number_of_threads = 5
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    # add a material database
    # sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    # world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_Si"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 20 * mm, 20 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # water slab
    water_slab_insert = sim.add_volume("Box", "water_slab_insert")
    water_slab_insert.mother = phantom_off.name
    water_slab_insert.size = [2 * mm, 20 * mm, 20 * mm]
    water_slab_insert.translation = [43 * mm, 0, 0]
    water_slab_insert.material = "G4_WATER"
    water_slab_insert.color = [0, 0, 1, 1]

    # si entrance
    entranceRegion = sim.add_volume("Box", "entranceRegion")
    entranceRegion.mother = phantom_off.name
    entranceRegion.size = [5 * mm, 20 * mm, 20 * mm]
    entranceRegion.translation = [47.5 * mm, 0, 0]
    entranceRegion.material = "G4_Si"
    entranceRegion.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_EMY"
    sim.physics_manager.global_production_cuts.all = 1000 * km
    # sim.set_cut("world", "all", 1000 * km)

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 40 * MeV
    source.particle = "proton"
    source.position.type = "disc"  # pos = Beam, shape = circle + sigma
    # rotate the disc, equiv to : rot1 0 1 0 and rot2 0 0 1
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    # source.position.radius = 8 * mm
    source.position.sigma_x = 2 * mm
    source.position.sigma_y = 2 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = 100

    # Define actors and collect them in a list for convenience (see below)
    dose_actors = []

    # each actor is attached to a different volume and/or scores in water/the local material
    dose_actor_IDD_d = sim.add_actor("DoseActor", "IDD_d")
    dose_actor_IDD_d.attached_to = phantom_off
    dose_actors.append(dose_actor_IDD_d)

    dose_actor_IDD_d2w = sim.add_actor("DoseActor", "IDD_d2w")
    dose_actor_IDD_d2w.attached_to = phantom_off
    dose_actor_IDD_d2w.score_in = "water"
    dose_actors.append(dose_actor_IDD_d2w)

    dose_actor_water_slab_insert_d = sim.add_actor("DoseActor", "IDD_waterSlab_d")
    dose_actor_water_slab_insert_d.attached_to = water_slab_insert
    dose_actors.append(dose_actor_water_slab_insert_d)

    dose_actor_water_slab_insert_d2w = sim.add_actor("DoseActor", "IDD_waterSlab_d2w")
    dose_actor_water_slab_insert_d2w.attached_to = water_slab_insert
    dose_actor_water_slab_insert_d2w.score_in = "water"
    dose_actors.append(dose_actor_water_slab_insert_d2w)

    dose_actor_entranceRegiont_d = sim.add_actor("DoseActor", "IDD_entranceRegion_d")
    dose_actor_entranceRegiont_d.attached_to = entranceRegion
    dose_actors.append(dose_actor_entranceRegiont_d)

    dose_actor_entranceRegiont_d2w = sim.add_actor(
        "DoseActor", "IDD_entranceRegion_d2w"
    )
    dose_actor_entranceRegiont_d2w.attached_to = entranceRegion
    dose_actor_entranceRegiont_d2w.score_in = "water"
    dose_actors.append(dose_actor_entranceRegiont_d2w)

    # set common properties
    # doing this is a loop keeps this script nicely compact
    for d in dose_actors:
        d.size = [1000, 1, 1]
        d.spacing = [0.1, 20.0, 20.0]
        d.output_filename = f"test041-{d.name}.mhd"
        d.dose.active = True  # the actor only scores edep by default, so we need to active dose scoring

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    # start simulation
    sim.run(start_new_process=True)

    # print results at the end
    print(stats)

    # ----------------------------------------------------------------------------------------------------------------
    # tests
    print("*** TESTING ***")

    # we can access the dose component of each actor
    # and ask it for the output path
    # so we do not need to manually keep track of the paths here in the script
    # syntax: dose_actor.dose.get_output_path()

    unused = utility.assert_images(
        dose_actor_IDD_d.dose.get_output_path(),
        dose_actor_IDD_d2w.dose.get_output_path(),
        stats,
        tolerance=100,
        ignore_value=0,
        axis="x",
    )

    mSPR_40MeV = 1.268771331  # from PSTAR NIST tables, Feb 2023
    mSPR_80MeV = 1.253197674  # from PSTAR NIST tables, Feb 2023
    gate.exception.warning(
        "Test ratio: dose / dose_to_water in geometry with material: G4_WATER"
    )
    is_ok = utility.assert_images_ratio(
        1.00,
        dose_actor_water_slab_insert_d.dose.get_output_path(),
        dose_actor_water_slab_insert_d2w.dose.get_output_path(),
        abs_tolerance=0.05,
    )

    gate.exception.warning(
        "Test ratio: dose / dose_to_water in geometry with material: G4_Si"
    )
    is_ok = (
        utility.assert_images_ratio(
            mSPR_40MeV,
            dose_actor_entranceRegiont_d.dose.get_output_path(),
            dose_actor_entranceRegiont_d2w.dose.get_output_path(),
            abs_tolerance=0.05,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
