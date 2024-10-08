#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility
import matplotlib.pyplot as plt


def simulate(number_of_dynamic_parametrisations=0):
    paths = utility.get_default_test_paths(
        __file__, "gate_test029_volume_time_rotation", "test030"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.random_seed = 983456
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    um = gate.g4_units.um
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second

    #  change world size
    sim.world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [20 * cm, 20 * cm, 20 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", -20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.set_production_cut("world", "all", 700 * um)

    # default source for tests
    # the source is fixed at the center, only the volume will move
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 5 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 30 * Bq

    # add dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.output_filename = "test030-edep.mhd"
    dose.attached_to = "waterbox"
    dose.size = [99, 99, 99]
    mm = gate.g4_units.mm
    dose.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose.translation = [2 * mm, 3 * mm, -2 * mm]
    dose.edep_uncertainty.active = True

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")

    # go
    sim.run(start_new_process=True)

    if number_of_dynamic_parametrisations > 1:
        # fake motion
        interval_length = 1 * sec / number_of_dynamic_parametrisations
        sim.run_timing_intervals = [
            (i * interval_length, (i + 1) * interval_length)
            for i in range(number_of_dynamic_parametrisations)
        ]
        # create a dynamic parametrisation which does actually not move anything
        # This is just to measure the run time overhead due to the call to BeginOfRunActionMasterThread()
        fake.add_dynamic_parametrisation(
            translation=number_of_dynamic_parametrisations * [fake.translation],
            rotation=number_of_dynamic_parametrisations * [fake.rotation],
        )

    # go
    sim.run(start_new_process=True)

    return stats.counts["duration"] / gate.g4_units["s"]


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test030")

    duration_static = simulate(0)
    n_dyn = [10, 100, 1000]
    durations = []
    for n in n_dyn:
        durations.append(simulate(n))

    print("********")
    print(f"The static simulation took {duration_static} sec")
    print(f"The dynamic simulations took: {duration_static} sec")
    for d, n in zip(durations, n_dyn):
        print(f"{d} sec for {n} dynamic parametrisations of translation and rotation")
    print("********")

    plt.figure()
    plt.scatter(n_dyn, durations, label="Dynamic simulation")
    plt.axhline(duration_static, label="Static simulation")
    plt.legend(loc="best")
    plt.xlabel("Number of dynamic parametrisations (translation, rotation)")
    plt.ylabel("Geant4 simulation run time in sec")
    plt.tight_layout()
    # plt.show()

    plt.savefig(paths.output / "run_time_dynamic_parametrisation.pdf")

    # FIXME: this is not really a test, always ok
