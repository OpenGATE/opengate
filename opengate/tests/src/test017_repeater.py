#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import opengate_core as g4
from scipy.spatial.transform import Rotation

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test017")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.check_volumes_overlap = True
    ui.random_seed = 254123

    #  change world size
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]

    # add a simple volume
    airBox = sim.add_volume("Box", "AirBox")
    cm = gate.g4_units.cm
    airBox.size = [30 * cm, 30 * cm, 30 * cm]
    airBox.translation = [0 * cm, 0 * cm, 0 * cm]
    airBox.material = "G4_AIR"
    airBox.color = [0, 0, 1, 1]  # blue

    # lyso material
    n = g4.G4NistManager.Instance()
    print(n)
    elems = ["Lu"]  # , 'Yttrium', 'Silicon', 'Oxygen']
    nbAtoms = [18]  # , 2, 10, 50]
    gcm3 = gate.g4_units.g_cm3
    n.ConstructNewMaterialNbAtoms("LYSO", elems, nbAtoms, 7.1 * gcm3)

    # repeat a box
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "AirBox"
    crystal.size = [1 * cm, 1 * cm, 1 * cm]
    crystal.translation = None
    crystal.rotation = None
    crystal.material = "LYSO"
    m = Rotation.identity().as_matrix()
    le = [
        {"name": "crystal1", "translation": [1 * cm, 0 * cm, 0], "rotation": m},
        {"name": "crystal2", "translation": [0.2 * cm, 2 * cm, 0], "rotation": m},
        {"name": "crystal3", "translation": [-0.2 * cm, 4 * cm, 0], "rotation": m},
        {"name": "crystal4", "translation": [0, 6 * cm, 0], "rotation": m},
    ]
    print(crystal)
    print(le)
    crystal.repeat = le

    # WARNING:
    # For large number of repetition, look test028 with RepeatParameterised volume
    # (it is more efficient)

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    source.particle = "gamma"
    source.energy.mono = 0.511 * MeV
    source.position.type = "sphere"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]
    source.activity = 10000 * Bq

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # dose actor
    d = sim.add_actor("DoseActor", "dose")
    d.output = paths.output / "test017-edep.mhd"
    # d.output = ref_path / 'test017-edep-ref.mhd'
    d.mother = "crystal"
    d.size = [150, 150, 150]
    d.spacing = [1 * mm, 1 * mm, 1 * mm]
    d.translation = [5 * mm, 0 * mm, 0 * mm]
    d.physical_volume_index = 0
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
    stats = sim.output.get_actor("Stats")
    # stats.write(ref_path / 'test017-stats-ref.txt')

    # tests
    stats_ref = utility.read_stat_file(paths.output_ref / "test017-stats-ref.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.04)
    is_ok = (
        utility.assert_images(
            paths.output_ref / "test017-edep-ref.mhd",
            paths.output / "test017-edep.mhd",
            stats,
            sum_tolerance=6,
            tolerance=70,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
