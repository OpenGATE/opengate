#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, "gate_test025_hits_collection")


def create_simulation(nb_threads):
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = nb_threads
    ui.check_volumes_overlap = False

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
    crystal1 = sim.add_volume("Box", "crystal1")
    crystal1.mother = "SPECThead"
    crystal1.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal1.translation = None
    crystal1.rotation = None
    crystal1.material = "NaITl"
    start = [-25 * cm, -20 * cm, 4 * cm]
    size = [100, 40, 1]
    # size = [100, 80, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal1.repeat = gate.geometry.utility.repeat_array_start(
        "crystal1", start, size, tr
    )
    crystal1.color = [1, 1, 0, 1]

    # additional volume
    crystal2 = sim.add_volume("Box", "crystal2")
    crystal2.mother = "SPECThead"
    crystal2.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal2.translation = None
    crystal2.rotation = None
    crystal2.material = "NaITl"
    start = [-25 * cm, 0 * cm, 4 * cm]
    size = [100, 40, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal2.repeat = gate.geometry.utility.repeat_array_start(
        "crystal2", start, size, tr
    )
    crystal2.color = [0, 1, 1, 1]

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
    source.activity = 50000 * Bq / ui.number_of_threads

    # add stat actor
    sim.add_actor("SimulationStatisticsActor", "Stats")

    # print list of attributes
    am = g4.GateDigiAttributeManager.GetInstance()
    print(am.GetAvailableDigiAttributeNames())

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.mother = [crystal1.name, crystal2.name]
    mt = ""
    if ui.number_of_threads > 1:
        mt = "_MT"
    hc.output = paths.output / ("test025_hits" + mt + ".root")
    hc.attributes = [
        "TotalEnergyDeposit",
        "KineticEnergy",
        "PostPosition",
        "TrackCreatorProcess",
        "GlobalTime",
        "TrackVolumeName",
        "RunID",
        "ThreadID",
        "TrackID",
    ]

    """
    ## NO DYNAMIC BRANCH YET --> bug in MT mode
    # dynamic branch creation (SLOW !)
    def branch_fill(att, step, touchable):
        e = step.GetTotalEnergyDeposit()
        att.FillDValue(e)
        # branch.push_back_double(e)
        # branch.push_back_double(123.3)
        # print('done')

    # dynamic branch
    man = gate_g4.GateDigiAttributeManager.GetInstance()
    man.DefineDigiAttribute('MyBranch', 'D', branch_fill)
    #hc.attributes.append('MyBranch')
    """

    print("List of active attributes (including dynamic attributes)", hc.attributes)

    # hits collection #2
    hc2 = sim.add_actor("DigitizerHitsCollectionActor", "Hits2")
    hc2.mother = [crystal1.name, crystal2.name]
    hc2.output = paths.output / ("test025_secondhits" + mt + ".root")
    hc2.attributes = ["TotalEnergyDeposit", "GlobalTime"]

    # --------------------------------------------------------------------------------------------------
    # create G4 objects
    sec = gate.g4_units.second
    sim.run_timing_intervals = [
        [0, 0.15 * sec],
        [0.15 * sec, 0.16 * sec],
        [0.16 * sec, 1 * sec],
    ]
    # sim.run_timing_intervals = [[0, 1 * sec]]
    # sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # ui.running_verbose_level = gate.EVENT
    return sim


def test_simulation_results(output):
    # Compare stats file
    stats = output.get_actor("Stats")
    print(f"Number of runs was {stats.counts.run_count}. Set to 1 before comparison")
    stats.counts.run_count = 1  # force to 1 to compare with gate result
    stats_ref = utility.read_stat_file(paths.gate_output / "stat.txt")
    is_ok = utility.assert_stats(stats, stats_ref, tolerance=0.05)

    # Compare root files
    print()
    gate_file = paths.gate_output / "hits.root"
    hc_file = output.get_actor("Hits").user_info.output
    checked_keys = ["posX", "posY", "posZ", "edep", "time", "trackId"]
    keys1, keys2, scalings, tols = utility.get_keys_correspondence(checked_keys)
    # tols[0] = 0.97   # PostPosition_X
    tols[3] = 0.002  # edep
    is_ok = (
        utility.compare_root3(
            gate_file,
            hc_file,
            "Hits",
            "Hits",
            keys1,
            keys2,
            tols,
            [1] * len(scalings),
            scalings,
            paths.output / "test025.png",
        )
        and is_ok
    )

    """# compare the dynamic branch
    print()
    t1 = uproot.open(gate_file)['Hits'].arrays(library="numpy")
    t2 = uproot.open(hc_file)['Hits'].arrays(library="numpy")
    gate.compare_branches(t1, list(t1.keys()), t2, list(t2.keys()),
                         'edep', 'MyBranch', 0.2, 1.0, False)"""

    # Compare root files
    print()
    gate_file = paths.gate_output / "hits.root"
    hc_file = output.get_actor("Hits2").user_info.output
    checked_keys = ["time", "edep"]
    keys1, keys2, scalings, tols = utility.get_keys_correspondence(checked_keys)
    tols[1] = 0.002  # edep
    is_ok = (
        utility.compare_root3(
            gate_file,
            hc_file,
            "Hits",
            "Hits2",
            keys1,
            keys2,
            tols,
            [1] * len(scalings),
            scalings,
            paths.output / "test025_secondhits.png",
        )
        and is_ok
    )

    # this is the end, my friend
    utility.test_ok(is_ok)
