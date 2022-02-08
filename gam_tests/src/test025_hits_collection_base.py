#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import gam_g4
import uproot
import pathlib
import matplotlib.pyplot as plt

paths = gam.get_common_test_paths(__file__, 'gate_test025_hits_collection')


def create_simulation(nb_threads):
    # create the simulation
    sim = gam.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = nb_threads
    ui.check_volumes_overlap = False

    # units
    m = gam.g4_units('m')
    cm = gam.g4_units('cm')
    keV = gam.g4_units('keV')
    mm = gam.g4_units('mm')
    Bq = gam.g4_units('Bq')

    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]

    # material
    sim.add_material_database(paths.data / 'GateMaterials.db')

    # fake spect head
    waterbox = sim.add_volume('Box', 'SPECThead')
    waterbox.size = [55 * cm, 42 * cm, 18 * cm]
    waterbox.material = 'G4_AIR'

    # crystal
    crystal1 = sim.add_volume('Box', 'crystal1')
    crystal1.mother = 'SPECThead'
    crystal1.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal1.translation = None
    crystal1.rotation = None
    crystal1.material = 'NaITl'
    start = [-25 * cm, -20 * cm, 4 * cm]
    size = [100, 40, 1]
    # size = [100, 80, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal1.repeat = gam.repeat_array('crystal1', start, size, tr)
    crystal1.color = [1, 1, 0, 1]

    # additional volume
    crystal2 = sim.add_volume('Box', 'crystal2')
    crystal2.mother = 'SPECThead'
    crystal2.size = [0.5 * cm, 0.5 * cm, 2 * cm]
    crystal2.translation = None
    crystal2.rotation = None
    crystal2.material = 'NaITl'
    start = [-25 * cm, 0 * cm, 4 * cm]
    size = [100, 40, 1]
    tr = [0.5 * cm, 0.5 * cm, 0]
    crystal2.repeat = gam.repeat_array('crystal2', start, size, tr)
    crystal2.color = [0, 1, 1, 1]

    # physic list
    p = sim.get_physics_user_info()
    p.physics_list_name = 'G4EmStandardPhysics_option4'
    p.enable_decay = False
    cuts = p.production_cuts
    cuts.world.gamma = 0.01 * mm
    cuts.world.electron = 0.01 * mm
    cuts.world.positron = 1 * mm
    cuts.world.proton = 1 * mm

    # default source for tests
    source = sim.add_source('Generic', 'Default')
    source.particle = 'gamma'
    source.energy.mono = 140.5 * keV
    source.position.type = 'sphere'
    source.position.radius = 4 * cm
    source.position.translation = [0, 0, -15 * cm]
    source.direction.type = 'momentum'
    source.direction.momentum = [0, 0, 1]
    source.activity = 5000 * Bq / ui.number_of_threads

    # add stat actor
    sim.add_actor('SimulationStatisticsActor', 'Stats')

    # hits collection
    hc = sim.add_actor('HitsCollectionActor', 'Hits')
    hc.mother = [crystal1.name, crystal2.name]
    mt = ''
    if ui.number_of_threads > 1:
        mt = '_MT'
    hc.output = paths.output / ('test025_hits' + mt + '.root')
    hc.attributes = ['TotalEnergyDeposit', 'KineticEnergy', 'PostPosition',
                     'CreatorProcess', 'GlobalTime', 'VolumeName', 'RunID', 'ThreadID', 'TrackID']

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
    man = gam_g4.GamHitAttributeManager.GetInstance()
    man.DefineHitAttribute('MyBranch', 'D', branch_fill)
    #hc.attributes.append('MyBranch')
    """

    print('List of active attributes (including dynamic attributes)', hc.attributes)

    # hits collection #2
    hc2 = sim.add_actor('HitsCollectionActor', 'Hits2')
    hc2.mother = [crystal1.name, crystal2.name]
    hc2.output = paths.output / ('test025_secondhits' + mt + '.root')
    hc2.attributes = ['TotalEnergyDeposit', 'GlobalTime']

    # --------------------------------------------------------------------------------------------------
    # create G4 objects
    sec = gam.g4_units('second')
    sim.run_timing_intervals = [[0, 0.15 * sec],
                                [0.15 * sec, 0.16 * sec],
                                [0.16 * sec, 1 * sec]
                                ]
    # sim.run_timing_intervals = [[0, 1 * sec]]
    # sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # ui.running_verbose_level = gam.EVENT
    return sim


def test_simulation_results(sim):
    # Compare stats file
    stats = sim.get_actor('Stats')
    print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
    stats.counts.run_count = 1  # force to 1 to compare with gate result
    stats_ref = gam.read_stat_file(paths.gate_output_ref / 'stat.txt')
    is_ok = gam.assert_stats(stats, stats_ref, tolerance=0.06)

    # Compare root files
    print()
    gate_file = paths.gate_output_ref / 'hits.root'
    hc_file = sim.get_actor_user_info("Hits").output
    checked_keys = ['posX', 'posY', 'posZ', 'edep', 'time', 'trackId']
    gam.compare_root(gate_file, hc_file, "Hits", "Hits", checked_keys, paths.output / 'test025.png')

    """# compare the dynamic branch
    print()
    t1 = uproot.open(gate_file)['Hits'].arrays(library="numpy")
    t2 = uproot.open(hc_file)['Hits'].arrays(library="numpy")
    gam.compare_branches(t1, list(t1.keys()), t2, list(t2.keys()),
                         'edep', 'MyBranch', 0.2, 1.0, False)"""

    # Compare root files
    print()
    gate_file = paths.gate_output_ref / 'hits.root'
    hc_file = sim.get_actor_user_info("Hits2").output
    checked_keys = ['time', 'edep']
    gam.compare_root(gate_file, hc_file, "Hits", "Hits2", checked_keys, paths.output / 'test025_secondhits.png')

    # this is the end, my friend
    gam.test_ok(is_ok)
