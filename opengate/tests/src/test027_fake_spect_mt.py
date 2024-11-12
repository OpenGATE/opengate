#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test027_fake_spect", "test027_fake_spect"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.number_of_threads = 2
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq

    # world size
    sim.world.size = [2 * m, 2 * m, 2 * m]

    # material
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

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
    source.activity = 5000 * Bq / sim.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = crystal.name
    hc.output_filename = "test027.root"
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
    sc.attached_to = crystal.name
    sc.input_digi_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    # sc.policy = 'EnergyWeightedCentroidPosition'
    # same filename, there will be two branches in the file
    sc.output_filename = hc.output_filename

    sec = gate.g4_units.second
    sim.running_verbose_level = 2
    sim.run_timing_intervals = [
        [0, 0.33 * sec],
        [0.33 * sec, 0.66 * sec],
        [0.66 * sec, 1 * sec],
    ]

    # start simulation
    sim.run()

    # stat
    gate.exception.warning("Compare stats")
    stats = sim.get_actor("Stats")
    print(stats)
    print(f"Number of runs was {stats.counts.runs}. Set to 1 before comparison")
    stats.counts.runs = 1  # force to 1
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.07)

    # root compare HITS
    print()
    gate.exception.warning("Compare HITS")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["posX", "posY", "posZ", "edep", "time", "trackId"]
    utility.compare_root(
        gate_file,
        hc.get_output_path(),
        "Hits",
        "Hits",
        checked_keys,
        paths.output / "test027.png",
    )

    # Root compare SINGLES
    print()
    gate.exception.warning("Compare SINGLES")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["globalposX", "globalposY", "globalposZ", "energy"]
    utility.compare_root(
        gate_file,
        sc.get_output_path(),
        "Singles",
        "Singles",
        checked_keys,
        paths.output / "test027_singles.png",
    )

    # this is the end, my friend
    utility.test_ok(is_ok)
