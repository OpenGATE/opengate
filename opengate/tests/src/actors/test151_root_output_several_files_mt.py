#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Several ROOT output files in a multithreaded simulation.

Three PhaseSpaceActors, attached to three thin planes, each write their own
ROOT file. In MT mode, the worker threads fill ntuples that Geant4 merges into
the file created by the master thread. On Windows, this used to crash for all
ROOT files but the first one ("ntuple id=1 does not exist", then an access
violation): the master and the workers did not compose the file name in the
same way when it contained '\' separators.

The world is vacuum, so every primary crosses the three planes: each ROOT file
must contain exactly one entry per event, for all the events.
"""

import opengate as gate
from opengate.tests import utility
import numpy as np
import uproot

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test151")

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV

    # simulation
    sim = gate.Simulation()
    sim.number_of_threads = 4
    sim.random_seed = 144144
    sim.output_dir = paths.output
    sim.check_volumes_overlap = False
    sim.progress_bar = False

    # world: vacuum, no interaction
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"

    # source: a beam along z
    n = 2000
    source = sim.add_source("GenericSource", "beam")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, -40 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = n

    # three thin planes, each with a phase space written in its own ROOT file
    phsps = []
    for i, z in enumerate([-20 * cm, 0 * cm, 20 * cm]):
        plane = sim.add_volume("Box", f"plane{i}")
        plane.material = "G4_Galactic"
        plane.size = [20 * cm, 20 * cm, 1 * nm]
        plane.translation = [0, 0, z]
        phsp = sim.add_actor("PhaseSpaceActor", f"phsp{i}")
        phsp.attached_to = plane
        phsp.attributes = ["EventID", "KineticEnergy", "ThreadID"]
        phsp.steps_to_store = "entering"
        phsp.output_filename = f"test151_phsp{i}.root"
        phsps.append(phsp)

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    # go
    sim.run()
    print(stats)

    # check: in each file, one entry per event, for all the events. In MT mode,
    # the event ids are unique but not consecutive, so the three files are
    # compared with each other: they must contain the same events.
    is_ok = stats.counts.events == n
    ref_event_ids = None
    for phsp in phsps:
        tree = uproot.open(phsp.get_output_path())[phsp.name]
        event_ids = np.sort(tree["EventID"].array(library="np"))
        energies = tree["KineticEnergy"].array(library="np")
        thread_ids = np.unique(tree["ThreadID"].array(library="np"))
        if ref_event_ids is None:
            ref_event_ids = event_ids
        ok = len(event_ids) == n
        ok = ok and len(np.unique(event_ids)) == n
        ok = ok and np.array_equal(event_ids, ref_event_ids)
        ok = ok and np.allclose(energies, 1 * MeV)
        utility.print_test(
            ok,
            f"{phsp.output_filename}: {len(event_ids)} entries (expected {n}), "
            f"threads {thread_ids.tolist()}",
        )
        is_ok = is_ok and ok

    utility.test_ok(is_ok)
