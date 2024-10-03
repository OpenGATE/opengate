#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

from scipy.spatial.transform import Rotation


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test008_dose_actor", output_folder="test012"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.number_of_threads = 2
    sim.random_seed = 123456789
    sim.check_volumes_overlap = True
    sim.output_dir = paths.output

    # shortcuts to units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    nm = gate.g4_units.nm

    #  change world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a simple fake volume to test hierarchy
    # translation and rotation like in the Gate macro
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.rotation = Rotation.from_euler("x", 10, degrees=True).as_matrix()
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # waterbox
    waterbox = sim.add_volume("Box", "waterbox")
    waterbox.mother = "fake"
    waterbox.size = [10 * cm, 10 * cm, 10 * cm]
    waterbox.translation = [-3 * cm, -2 * cm, -1 * cm]
    waterbox.rotation = Rotation.from_euler("y", 20, degrees=True).as_matrix()
    waterbox.material = "G4_WATER"
    waterbox.color = [0, 0, 1, 1]

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.radius = 1 * nm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    # source.activity = 2e5 / sim.number_of_threads * Bq
    source.activity = 5e4 / sim.number_of_threads * Bq

    """
    It needs at least around 2e5 particles for the multithread to be faster than mono thread
    """

    # add dose actor
    dose_actor = sim.add_actor("DoseActor", "dose_actor")
    dose_actor.edep.output_filename = "test012-edep.mhd"
    dose_actor.attached_to = "waterbox"
    dose_actor.size = [99, 99, 99]
    dose_actor.spacing = [2 * mm, 2 * mm, 2 * mm]
    dose_actor.translation = [2 * mm, 3 * mm, -2 * mm]

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True

    # print info
    sim.volume_manager.print_volumes()

    # verbose
    # sim.g4_commands_after_init.append('/tracking/verbose 0')
    sim.g4_commands_after_init.append("/run/verbose 2")
    # sim.g4_commands_after_init.append("/event/verbose 2")
    # sim.g4_commands_after_init.append("/tracking/verbose 1")

    # start simulation
    sim.run()

    # print results at the end
    print(stat)
    print(dose_actor)

    # tests
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    # change the number of run to the number of threads
    stats_ref.counts.runs = sim.number_of_threads
    is_ok = utility.assert_stats(stat, stats_ref, 0.10)

    is_ok = (
        utility.assert_images(
            paths.gate_output / "output-Edep.mhd",
            dose_actor.edep.get_output_path(),
            stat,
            tolerance=45,
        )
        and is_ok
    )
    utility.test_ok(is_ok)
