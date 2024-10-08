#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate_core as g4

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test017")

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.check_volumes_overlap = True
    sim.random_seed = 254123
    sim.output_dir = paths.output

    #  change world size
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3

    sim.world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # add a simple volume
    airBox = sim.add_volume("Box", "AirBox")
    airBox.size = [30 * cm, 30 * cm, 30 * cm]
    airBox.translation = [0 * cm, 0 * cm, 0 * cm]
    airBox.material = "G4_AIR"
    airBox.color = [0, 0, 1, 1]  # blue

    # lyso material
    n = g4.G4NistManager.Instance()
    print(n)
    elems = ["Lu"]  # , 'Yttrium', 'Silicon', 'Oxygen']
    nbAtoms = [18]  # , 2, 10, 50]
    n.ConstructNewMaterialNbAtoms("LYSO", elems, nbAtoms, 7.1 * gcm3)

    # repeat a box
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "AirBox"
    crystal.size = [1 * cm, 1 * cm, 1 * cm]
    # assign 4 translations -> this will create 4 physical copies of this volume in space
    crystal.translation = [
        [1 * cm, 0 * cm, 0],
        [0.2 * cm, 2 * cm, 0],
        [-0.2 * cm, 4 * cm, 0],
        [0, 6 * cm, 0],
    ]
    crystal.material = "LYSO"
    print(crystal)

    # WARNING:
    # For large number of repetition, look at test028 with RepeatParameterised volume
    # (it is more efficient)

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 0.511 * MeV
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]
    source.activity = 10000 * Bq

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # dose actor
    dose = sim.add_actor("DoseActor", "dose")
    dose.edep.output_filename = "test017.mhd"
    # dose.output = ref_path / 'test017-edep-ref.mhd'
    dose.attached_to = "crystal"
    dose.size = [150, 150, 150]
    dose.spacing = [1 * mm, 1 * mm, 1 * mm]
    dose.translation = [5 * mm, 0 * mm, 0 * mm]
    print(
        "The Dose actor is triggered every time a hit occurs in the (logical volume) "
        '"crystal" (and any of its associated repeated physical volumes).'
    )
    print(
        "The Dose actor is attached to the first (repeated) crystal, it moves with its coord system."
    )

    # start simulation
    sim.run()

    # print results
    print(stats)

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test017-stats-ref.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.04)
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test017-edep-ref.mhd",
            dose.edep.get_output_path(),
            stats,
            sum_tolerance=6,
            tolerance=70,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
