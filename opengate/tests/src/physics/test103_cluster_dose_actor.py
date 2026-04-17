#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itk
import numpy as np

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test103")

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 123456
    sim.number_of_threads = 1

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "QGSP_BIC_EMY"

    source = sim.add_source("GenericSource", "source")
    source.particle = "proton"
    source.energy.mono = 20 * MeV
    source.position.type = "disc"
    source.position.radius = 2 * mm
    source.position.translation = [0, 0, -3 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 200

    database_path = paths.output / "ionization_parameter_database.txt"
    database = np.array(
        [
            [0.0, 0.0],
            [5.0, 2.5],
            [10.0, 5.0],
            [20.0, 10.0],
            [30.0, 15.0],
        ]
    )
    np.savetxt(database_path, database)

    actor = sim.add_actor("ClusterDoseActor", "cluster_dose_actor")
    actor.attached_to = phantom.name
    actor.size = [20, 20, 20]
    actor.spacing = [5 * mm, 5 * mm, 5 * mm]
    actor.ionization_parameter = "cluster_size_2"
    actor.database = database_path
    actor.hit_type = "random"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    sim.run(start_new_process=True)

    image = actor.cluster_dose.image
    numerator = actor.cluster_dose_numerator.image
    denominator = actor.cluster_dose_denominator.image
    array = itk.array_view_from_image(image)
    numerator_array = itk.array_view_from_image(numerator)
    denominator_array = itk.array_view_from_image(denominator)

    print(stats)
    print(actor)
    print(f"Cluster dose sum: {np.sum(array)}")

    is_ok = True
    is_ok = is_ok and image is not None
    is_ok = is_ok and numerator is not None
    is_ok = is_ok and denominator is not None
    is_ok = is_ok and array.dtype == np.float64
    is_ok = is_ok and array.ndim == 3
    is_ok = is_ok and np.sum(array) > 0
    is_ok = is_ok and np.sum(numerator_array) > 0
    is_ok = is_ok and np.sum(denominator_array) > 0
    is_ok = is_ok and np.max(array) > 0

    utility.test_ok(is_ok)
