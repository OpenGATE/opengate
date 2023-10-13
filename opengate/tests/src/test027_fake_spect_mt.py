#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test027_fake_spect")

    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = 2

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq

    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # material
    sim.add_material_database(paths.data / "GateMaterials.db")

    # fake spect head
    waterbox = sim.add_volume("Box", "SPECThead")
    waterbox.size = [55 * cm, 42 * cm, 18 * cm]
    waterbox.material = "G4_AIR"

    # crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "SPECThead"
    crystal.size = [55 * cm, 42 * cm, 2 * cm]
    crystal.translation = [0, 0, 4 * cm]
    crystal.material = "NaITl"
    crystal.color = [1, 1, 0, 1]

    # colli
    """colli = sim.add_volume('Box', 'colli')
    colli.mother = 'SPECThead'
    colli.size = [55 * cm, 42 * cm, 6 * cm]
    colli.material = 'Lead'
    hole = sim.add_volume('Polyhedra', 'hole')
    hole.mother = 'colli'
    h = 5.8 * cm
    hole.zplane = [-h / 2, h - h / 2]
    hole.radius_outer = [0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm]
    hole.translation = None
    hole.rotation = None

    size = [77, 100, 1]
    #size = [7, 10, 1]
    tr = [7.01481 * mm, 4.05 * mm, 0]

    ## not correct position
    start = [-(size[0] * tr[0]) / 2.0, -(size[1] * tr[1]) / 2.0, 0]
    r1 = gate.geometry.utility.repeat_array('colli1', start, size, tr)
    start[0] += 3.50704 * mm
    start[1] += 2.025 * mm
    r2 = gate.geometry.utility.repeat_array('colli2', start, size, tr)
    hole.repeat = r1 + r2"""

    # physic list
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.enable_decay = False
    sim.physics_manager.global_production_cuts.gamma = 0.01 * mm
    sim.physics_manager.global_production_cuts.electron = 0.01 * mm
    sim.physics_manager.global_production_cuts.positron = 1 * mm
    sim.physics_manager.global_production_cuts.proton = 1 * mm

    # default source for tests
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 4 * cm
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 5000 * Bq / ui.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.mother = crystal.name
    hc.output = paths.output / "test027.root"
    hc.attributes = [
        "KineticEnergy",
        "PostPosition",
        "PrePosition",
        "TotalEnergyDeposit",
        "GlobalTime",
        "TrackVolumeName",
        "TrackID",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "TrackVolumeCopyNo",
        "TrackVolumeInstanceID",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.mother = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    # sc.policy = 'EnergyWeightedCentroidPosition'
    # same filename, there will be two branches in the file
    sc.output = hc.output

    sec = gate.g4_units.second
    ui.running_verbose_level = 2
    sim.run_timing_intervals = [
        [0, 0.33 * sec],
        [0.33 * sec, 0.66 * sec],
        [0.66 * sec, 1 * sec],
    ]

    # start simulation
    sim.run()

    # stat
    gate.exception.warning("Compare stats")
    stats = sim.output.get_actor("Stats")
    print(stats)
    print(f"Number of runs was {stats.counts.run_count}. Set to 1 before comparison")
    stats.counts.run_count = 1  # force to 1
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.07)

    # root compare HITS
    print()
    gate.exception.warning("Compare HITS")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["posX", "posY", "posZ", "edep", "time", "trackId"]
    utility.compare_root(
        gate_file, hc.output, "Hits", "Hits", checked_keys, paths.output / "test027.png"
    )

    # Root compare SINGLES
    print()
    gate.exception.warning("Compare SINGLES")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["globalposX", "globalposY", "globalposZ", "energy"]
    utility.compare_root(
        gate_file,
        sc.output,
        "Singles",
        "Singles",
        checked_keys,
        paths.output / "test027_singles.png",
    )

    # this is the end, my friend
    utility.test_ok(is_ok)
