#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test102_debug_actor")

    # create the simulation
    sim = gate.Simulation()
    sim.visu = False
    sim.random_seed = "auto"
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.store_json_archive = True
    print(paths)

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # fake volume
    fake = sim.add_volume("Box", "fake")
    fake.size = [40 * cm, 40 * cm, 40 * cm]
    fake.translation = [1 * cm, 2 * cm, 3 * cm]
    fake.rotation = Rotation.from_euler("x", 10, degrees=True).as_matrix()
    fake.material = "G4_AIR"
    fake.color = [1, 0, 1, 1]

    # debug source
    debug_source = sim.add_source("DebugSource", "debug_source")
    debug_source.n = 3
    debug_source.debug_flag = True

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True

    # start simulation in another process
    sim.run(start_new_process=True)
    # sim.run()

    # print results at the end
    print(stat)
    print(debug_source)

    print(f"Simulation json saved in {sim.output_dir / sim.json_archive_filename}")

    # assertions to verify MT execution and output recovery
    assert stat.counts.events == 3 * sim.number_of_threads
    assert stat.counts.runs == sim.number_of_threads

    assert hasattr(debug_source, "debug_flag")
    assert debug_source.debug_flag == True

    assert hasattr(debug_source, "debug_value")
    assert debug_source.debug_value == 3

    is_ok = True
    utility.test_ok(is_ok)
