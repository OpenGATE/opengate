#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
from scipy.spatial.transform import Rotation
import uproot
import matplotlib.pyplot as plt

paths = gate.get_default_test_paths(__file__, "gate_test036_adder_depth")


def create_simulation(geom):
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = 1
    ui.random_seed = 123456

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    nm = gate.g4_units("nm")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    kBq = 1000 * Bq

    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # material
    sim.add_material_database(paths.data / "GateMaterials.db")

    # fake spect head
    head = sim.add_volume("Box", "SPECThead")
    head.size = [55 * cm, 42 * cm, 18 * cm]
    head.translation = [0, 0, 15 * cm]  ## not use if array of 2 heads
    head.material = "G4_AIR"

    # crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "SPECThead"
    crystal.size = [55 * cm, 42 * cm, 2 * cm]
    crystal.translation = [0, 0, 4 * cm]
    crystal.material = "Plastic"
    crystal.color = [1, 0, 0, 1]

    # pixel crystal
    crystal_pixel = sim.add_volume("Box", "crystal_pixel")
    crystal_pixel.mother = crystal.name
    crystal_pixel.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal_pixel.material = "NaITl"
    crystal_pixel.color = [1, 1, 0, 1]

    # geom
    size = [110, 84, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]

    if geom == "repeat":
        le = gate.repeat_array(crystal_pixel.name, size, tr)
        crystal_pixel.translation = None
        crystal_pixel.rotation = None
        crystal_pixel.repeat = le

    if geom == "param":
        crystal_repeater = gate.build_param_repeater(
            sim, crystal.name, crystal_pixel.name, size, tr
        )

    # FIXME add a second head
    head.translation = None
    head.rotation = None
    tr = 30 * cm
    le = gate.repeat_array(head.name, [1, 1, 2], [0, 0, tr])
    le[0]["rotation"] = Rotation.from_euler("X", 180, degrees=True).as_matrix()
    head.repeat = le

    # physic list
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    p.enable_decay = False
    cuts = p.production_cuts
    cuts.world.gamma = 0.01 * mm
    cuts.world.electron = 0.01 * mm
    cuts.world.positron = 1 * mm
    cuts.world.proton = 1 * mm

    # default source for tests
    activity = 40 * kBq / ui.number_of_threads
    # activity = 5 * Bq / ui.number_of_threads
    source = sim.add_source("Generic", "src1")
    source.particle = "gamma"
    source.energy.mono = 333 * keV
    source.position.type = "sphere"
    source.position.radius = 5 * cm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = activity

    # default source for tests
    source = sim.add_source("Generic", "src2")
    source.particle = "gamma"
    source.energy.mono = 222 * keV
    source.position.type = "sphere"
    source.position.radius = 5 * cm
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.activity = activity

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("HitsCollectionActor", "Hits")
    hc.mother = crystal.name
    hc.output = paths.output / "test036.root"
    hc.attributes = [
        "KineticEnergy",
        "PostPosition",
        # 'HitPosition', 'PrePosition',
        "TotalEnergyDeposit",
        "GlobalTime",  # 'EventID',
        # 'TrackVolumeName', 'TrackID',  # 'Test',
        # 'ProcessDefinedStep',
        "PostStepUniqueVolumeID",
        # 'TrackVolumeCopyNo', 'TrackVolumeInstanceID'
    ]

    # singles collection
    sc = sim.add_actor("HitsAdderActor", "Singles")
    sc.mother = crystal.name
    sc.input_hits_collection = "Hits"
    # sc.policy = 'EnergyWinnerPosition'
    sc.policy = "EnergyWeightedCentroidPosition"
    # same filename, there will be two branches in the file
    sc.output = hc.output

    sec = gate.g4_units("second")
    ui.running_verbose_level = 2
    # sim.run_timing_intervals = [[0, 0.33 * sec], [0.33 * sec, 0.66 * sec], [0.66 * sec, 1 * sec]]

    # create G4 objects
    sim.initialize()

    # print cuts
    pm = sim.physics_manager
    print(pm.dump_cuts_initialized())

    return sim


def test_output(sim):
    # retrieve the information about the touched volumes
    man = g4.GateUniqueVolumeIDManager.GetInstance()
    vols = man.GetAllVolumeIDs()
    print(f"There are {len(vols)} volumes used in the adder")
    """for v in vols:
        vid = v.GetVolumeDepthID()
        print(f'Volume {v.fID}: ', end='')
        for x in vid:
            print(f' {x.fDepth} {x.fVolumeName} {x.fCopyNb} / ', end='')
        print()"""

    # stat
    gate.warning("Compare stats")
    stats = sim.get_actor("Stats")
    print(stats)
    print(f"Number of runs was {stats.counts.run_count}. Set to 1 before comparison")
    stats.counts.run_count = 1  # force to 1
    stats_ref = gate.read_stat_file(paths.gate_output / "stats.txt")
    is_ok = gate.assert_stats(stats, stats_ref, tolerance=0.07)

    # root compare HITS
    print()
    hc = sim.get_actor_user_info("Hits")
    gate.warning("Compare HITS")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["posX", "posY", "posZ", "edep", "time", "trackId"]
    keys1, keys2, scalings, tols = gate.get_keys_correspondence(checked_keys)
    tols[2] = 2  # Z
    # tols[4] = 0.01  # energy
    gate.compare_root3(
        gate_file,
        hc.output,
        "Hits",
        "Hits",
        keys1,
        keys2,
        tols,
        scalings,
        scalings,
        paths.output / "test036_hits.png",
    )

    # Root compare SINGLES
    print()
    sc = sim.get_actor_user_info("Singles")
    gate.warning("Compare SINGLES")
    gate_file = paths.gate_output / "spect.root"
    checked_keys = ["time", "globalPosX", "globalPosY", "globalPosZ", "energy"]
    keys1, keys2, scalings, tols = gate.get_keys_correspondence(checked_keys)
    tols[3] = 0.9  # Z
    # tols[1] = 1.0  # X
    # tols[2] = 1.0  # Y
    # tols[4] = 0.02  # energy
    gate.compare_root3(
        gate_file,
        sc.output,
        "Singles",
        "Singles",
        keys1,
        keys2,
        tols,
        scalings,
        scalings,
        paths.output / "test036_singles.png",
    )

    # this is the end, my friend
    return is_ok
