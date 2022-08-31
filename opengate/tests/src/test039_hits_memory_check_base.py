#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "")


def create_simu(nb_threads):
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = nb_threads
    ui.random_seed = "auto"  # 123456
    ui.check_volumes_overlap = False

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # material
    sim.add_material_database(paths.data / "GateMaterials.db")

    # fake spect head
    waterbox = sim.add_volume("Box", "spect")
    waterbox.size = [55 * cm, 42 * cm, 18 * cm]
    waterbox.material = "G4_AIR"

    # crystal
    crystal = sim.add_volume("Box", "crystal")
    crystal.mother = "spect"
    crystal.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal.translation = None
    crystal.rotation = None
    crystal.material = "NaITl"
    start = [-25 * cm, -20 * cm, 4 * cm]
    size = [100, 80, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal.repeat = gate.repeat_array_start("crystal", start, size, tr)
    crystal.color = [1, 1, 0, 1]

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
    source = sim.add_source("Generic", "Default")
    source.particle = "gamma"
    source.energy.mono = 140.5 * keV
    source.position.type = "sphere"
    source.position.radius = 4 * cm
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 200000 * Bq / ui.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # hits collection
    hc = sim.add_actor("HitsCollectionActor", "Hits")
    hc.mother = crystal.name
    hc.output = ""  # paths.output / 'test039_hits.root'
    hc.clear_every = 1
    hc.attributes = [
        "TotalEnergyDeposit",
        "KineticEnergy",
        "PostPosition",
        "PostStepUniqueVolumeID",
        "TrackCreatorProcess",
        "GlobalTime",
        "TrackVolumeName",
        "RunID",
        "ThreadID",
        "TrackID",
    ]

    sc = sim.add_actor("HitsAdderActor", "Singles")
    sc.mother = crystal.name
    sc.input_hits_collection = "Hits"
    sc.policy = "EnergyWinnerPosition"
    sc.clear_every = 333
    sc.output = paths.output / "test039_singles.root"

    cc = sim.add_actor("HitsEnergyWindowsActor", "EnergyWindows")
    cc.mother = crystal.name
    cc.input_hits_collection = "Singles"
    cc.clear_every = 10
    cc.channels = [
        {"name": "scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": "peak140", "min": 126 * keV, "max": 154.55 * keV},
        {
            "name": "spectrum",
            "min": 0 * keV,
            "max": 5000 * keV,
        },  # should be strictly equal to 'Singles'
    ]
    cc.output = paths.output / "test039_win_e.root"

    return sim


# go
# sim.initialize()
# sim.start()

# On linux
# valgrind --tool=massif --massif-out-file=./massif_t039_no_cleared.out  python test039_hits_memory_check_MP.py
# valgrind --tool=massif --massif-out-file=./massif_t039_cleared.out  python test039_hits_memory_check_MP.py
# test with clear_every = 1e8 (no-cleared) and with clear_every = 1 (cleared)

"""ms_print arguments: massif_t039_no_cleared.out
--------------------------------------------------------------------------------

    MB
722.9^                                             ##
     |                                             # :::::::@::::::@::::::::::
     |                                         @   # ::: :::@::::::@::       :
     |                                         @:::# ::: :::@::::::@::       :
     |                                         @:::# ::: :::@::::::@::       :
     |                                       ::@:::# ::: :::@::::::@::       :
     |                                       : @:::# ::: :::@::::::@::       :
     |                                      :: @:::# ::: :::@::::::@::       :
     |                              @       :: @:::# ::: :::@::::::@::       :
     |                             @@::::::::: @:::# ::: :::@::::::@::       :
     |                           ::@@::::::::: @:::# ::: :::@::::::@::       :
     |                           ::@@::::::::: @:::# ::: :::@::::::@::       :
     |                         ::::@@::::::::: @:::# ::: :::@::::::@::       :
     |                      :::::::@@::::::::: @:::# ::: :::@::::::@::       :
     |                    :::::::::@@::::::::: @:::# ::: :::@::::::@::       :
     |                  :::::::::::@@::::::::: @:::# ::: :::@::::::@::       :
     |                 ::::::::::::@@::::::::: @:::# ::: :::@::::::@::       :
     |          @:@@:::::::::::::::@@::::::::: @:::# ::: :::@::::::@::       :
     |   ::@:::@@:@@:::::::::::::::@@::::::::: @:::# ::: :::@::::::@::       :
     | ::::@:::@@:@@:::::::::::::::@@::::::::: @:::# ::: :::@::::::@::       :
   0 +----------------------------------------------------------------------->Gi
     0                                                                   143.9
"""

"""ms_print arguments: massif_t039_cleared.out
    MB
154.3^                                                #
     |                :@:::::@::::::::::@:::::::::::@:#::::@::::@::::@@@@@@@@
     |               ::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |             @:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |             @:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |           ::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |         ::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |        @::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |     :::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |    @:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |    @:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |  ::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |  ::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     | :::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
     |@:::@:::@::::@:::@:::::@::::::::::@:::::::::::@:#::::@::::@::::@       :
   0 +----------------------------------------------------------------------->Gi
     0                                                                   144.0
"""


def test_results(sim):
    # Compare stats file
    stats = sim.get_actor("Stats")
    # stats.write(paths.output_ref / 'test039_stats.txt')
    print(stats)
    stats_ref = gate.read_stat_file(paths.output_ref / "test039_stats.txt")
    stats.counts.run_count = 2  # sim.user_info.number_of_threads
    is_ok = gate.assert_stats(stats, stats_ref, 0.05)

    # Compare singles
    print()
    sc = sim.get_actor_user_info("Singles")
    gate.warning(f"Check singles")
    ref_file = paths.output_ref / "test039_singles.root"
    hc_file = sc.output
    checked_keys = [
        "GlobalTime",
        "TotalEnergyDeposit",
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
    ]
    scalings = [1.0] * len(checked_keys)
    tols = [10.0] * len(checked_keys)
    scalings[checked_keys.index("GlobalTime")] = 1e-9  # time in ns
    tols[checked_keys.index("GlobalTime")] = 0.003
    tols[checked_keys.index("TotalEnergyDeposit")] = 0.001
    tols[checked_keys.index("PostPosition_X")] = 0.2
    tols[checked_keys.index("PostPosition_Y")] = 0.2
    tols[checked_keys.index("PostPosition_Z")] = 0.2
    print(scalings, tols)
    is_ok = (
        gate.compare_root3(
            ref_file,
            hc_file,
            "Singles",
            "Singles",
            checked_keys,
            checked_keys,
            tols,
            scalings,
            scalings,
            paths.output / "test039_singles.png",
            hits_tol=1,
        )
        and is_ok
    )

    return is_ok
    # this is the end, my friend
    # gate.delete_run_manager_if_needed(sim)
    # gate.test_ok(is_ok)
