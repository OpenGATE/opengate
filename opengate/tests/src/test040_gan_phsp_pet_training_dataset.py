#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test040")

    # create the simulation
    sim = gate.Simulation()

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3
    sec = gate.g4_units.second
    deg = gate.g4_units.deg
    kBq = 1000 * Bq
    MBq = 1000 * kBq

    # main parameters
    sim.output_dir = paths.output
    sim.check_volumes_overlap = True
    sim.number_of_threads = 1
    sim.random_seed = 123456789
    sim.output_dir = paths.output
    ac = 15 * BqmL
    sim.visu = False
    if sim.visu:
        ac = 10 * BqmL  # per mL
        sim.number_of_threads = 1

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # iec phantom
    iec_phantom = gate_iec.add_iec_phantom(sim)

    # cylinder for phsp
    sph_surface = sim.add_volume("Sphere", "phase_space_sphere")
    sph_surface.rmin = 210 * mm
    sph_surface.rmax = 211 * mm
    sph_surface.color = [0, 1, 0, 1]
    sph_surface.material = "G4_AIR"

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # source sphere
    gate_iec.add_spheres_sources(
        sim,
        "iec",
        "source1",
        [10, 13, 17, 22, 28, 37],
        [ac, ac, ac, ac, ac, ac],
        verbose=True,
    )

    sources = sim.source_manager.user_info_sources
    for source in sources.values():
        source.particle = "e+"
        source.energy.type = "Ga68"

    # background source 1:7 ratio with sphere
    bg = gate_iec.add_background_source(sim, "iec", "source_bg", ac / 7, verbose=True)
    bg.particle = "e+"
    bg.energy.type = "Ga68"

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "test040_train_stats.txt"

    # filter gamma only
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"

    # phsp
    phsp = sim.add_actor("PhaseSpaceActor", "phase_space")
    phsp.attached_to = "phase_space_sphere"
    # we use PrePosition because this is the first step in the volume
    phsp.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PreDirection",
        "TimeFromBeginOfEvent",
        # needed for gan_flag
        "EventID",
        "EventKineticEnergy",
        # for conditional :
        "EventPosition",
        "EventDirection",
    ]
    phsp.output_filename = "test040_train.root"
    phsp.store_absorbed_event = (
        True  # this option allow to store all events even if absorbed
    )
    phsp.filters.append(f)
    print(phsp)
    print(phsp.get_output_path())

    # go
    sim.run()

    # ----------------------------------------------------------------------------------------------------------

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    print(stats)
    stats_ref = utility.read_stat_file(paths.output_ref / "test040_train_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.03)

    # check phsp
    print()
    gate.exception.warning(f"Check root")
    p = sim.get_actor("phase_space")
    print(f"Number of absorbed : {p.number_of_absorbed_events}")
    ref_file = paths.output_ref / "test040_train.root"
    hc_file = phsp.get_output_path()
    checked_keys = [
        "TimeFromBeginOfEvent",
        "KineticEnergy",
        "PrePosition_X",
        "PrePosition_Y",
        "PrePosition_Z",
        "PreDirection_X",
        "PreDirection_Y",
        "PreDirection_Z",
        "EventKineticEnergy",
        "EventPosition_X",
        "EventPosition_Y",
        "EventPosition_Z",
        "EventDirection_X",
        "EventDirection_Y",
        "EventDirection_Z",
    ]
    scalings = [1] * len(checked_keys)
    # scalings[0] = 1e-9  # time in ns
    tols = [1.0] * len(checked_keys)
    tols[checked_keys.index("TimeFromBeginOfEvent")] = 0.007
    tols[checked_keys.index("KineticEnergy")] = 0.003
    tols[checked_keys.index("PrePosition_X")] = 1.7
    tols[checked_keys.index("PrePosition_Y")] = 1.6
    tols[checked_keys.index("PrePosition_Z")] = 1.9
    tols[checked_keys.index("PreDirection_X")] = 0.01
    tols[checked_keys.index("PreDirection_Y")] = 0.01
    tols[checked_keys.index("PreDirection_Z")] = 0.01
    tols[checked_keys.index("EventKineticEnergy")] = 0.02
    tols[checked_keys.index("EventPosition_X")] = 1.8
    tols[checked_keys.index("EventPosition_Y")] = 1.8
    tols[checked_keys.index("EventPosition_Z")] = 1.8
    tols[checked_keys.index("EventDirection_X")] = 0.02
    tols[checked_keys.index("EventDirection_Y")] = 0.02
    tols[checked_keys.index("EventDirection_Z")] = 0.02
    print(scalings, tols)
    is_ok = (
        utility.compare_root3(
            ref_file,
            hc_file,
            "phase_space",
            "phase_space",
            checked_keys,
            checked_keys,
            tols,
            scalings,
            scalings,
            paths.output / "test040_train_phsp.png",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
