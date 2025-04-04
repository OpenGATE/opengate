#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np

from opengate.actors.biasingactors import distance_dependent_angle_tolerance
from opengate.tests import utility
from test085_free_flight_helpers import *

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, output_folder="test089")

    # create the simulation
    sim = gate.Simulation()
    sim.number_of_threads = 1
    sim.visu_type = "qt"
    # sim.visu = True
    sim.random_seed = "auto"
    sim.progress_bar = True
    sim.output_dir = paths.output
    sim.random_seed = "auto"

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * m)

    # volumes
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"
    radius = 28 * cm
    actors, heads = add_spect_heads(sim, "test089", radius)

    box = sim.add_volume("BoxVolume", "box")
    box.size = [0.2 * cm, 25 * cm, 0.2 * cm]
    box.translation = [10 * cm, 1 * cm, 0]
    box.material = "G4_Galactic"
    box.color = [1, 0, 0, 1]

    box2 = sim.add_volume("BoxVolume", "box2")
    box2.size = box.size.copy()
    box2.translation = [-10 * cm, 1 * cm, 0]
    box2.material = "G4_Galactic"
    box2.color = [0, 0, 1, 1]

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    # change the source
    source = sim.add_source("GenericSource", "src")
    source.attached_to = "box"
    source.particle = "gamma"
    set_source_energy_spectrum(source, "tc99m", "radar")
    source.position.type = "box"
    source.position.size = box.size
    source.direction.type = "iso"
    source.activity = 1e4 * gate.g4_units.Bq

    source.direction.acceptance_angle.skip_policy = "SkipEvents"
    source.direction.acceptance_angle.intersection_flag = True
    source.direction.acceptance_angle.normal_flag = True
    source.direction.acceptance_angle.volumes = ["spect_1"]
    source.direction.acceptance_angle.normal_vector = [0, 0, -1]
    source.direction.acceptance_angle.normal_tolerance = 20 * gate.g4_units.deg
    source.direction.acceptance_angle.distance_dependent_normal_tolerance = True
    source.direction.acceptance_angle.angle1 = 80 * gate.g4_units.degree
    source.direction.acceptance_angle.distance1 = 10 * cm
    source.direction.acceptance_angle.angle2 = 5 * gate.g4_units.degree
    source.direction.acceptance_angle.distance2 = 30 * cm

    # another source
    source2 = sim.source_manager.add_source_copy("src", "src2")
    source2.attached_to = "box2"
    source2.direction.acceptance_angle.distance_dependent_normal_tolerance = False

    # free flight actor
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)
    ff = sim.add_actor("GammaFreeFlightActor", "ff")
    ff.attached_to = "world"
    ff.ignored_volumes = ["spect_1", "spect_2"]

    # plot dd
    a1 = source.direction.acceptance_angle.angle1
    a2 = source.direction.acceptance_angle.angle2
    d1 = source.direction.acceptance_angle.distance1
    d2 = source.direction.acceptance_angle.distance2
    distances = np.linspace(d1 / 2, d2 * 2, 200)
    angles = [distance_dependent_angle_tolerance(a1, a2, d1, d2, d) for d in distances]

    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 6))
    plt.plot(distances / cm, np.degrees(angles), label="Distance vs Angle")
    plt.xlabel("Distance (cm)")
    plt.ylabel("Angle (degrees)")
    plt.title("Distance vs Angle Tolerance")
    plt.grid()
    plt.legend()
    # plt.show()
    f = paths.output / "ddaa.png"
    plt.savefig(f)

    # go
    sim.run()
    print(stats)
    print(f"Saved ddaa plot to {f}")
