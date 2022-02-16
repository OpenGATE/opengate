#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_linac as gam_linac
import gatetools.phsp as phsp
import matplotlib.pyplot as plt

paths = gam.get_common_test_paths(__file__, 'gate_test019_linac_phsp')


def init_test019(nt):
    # global log level
    # create the simulation
    sim = gam.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.check_volumes_overlap = False
    ui.number_of_threads = nt
    print(ui)

    # units
    m = gam.g4_units('m')
    mm = gam.g4_units('mm')
    cm = gam.g4_units('cm')
    nm = gam.g4_units('nm')

    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]

    # add a waterbox
    # waterbox = sim.add_volume('Box', 'Waterbox')
    # waterbox.size = [30 * cm, 30 * cm, 30 * cm]
    # waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
    # waterbox.material = 'G4_WATER'
    # waterbox.color = [0, 0, 1, 1]  # blue

    # add a linac
    linac = gam_linac.add_linac(sim, 'linac')
    linac.translation = [0, 0, 0 * m]

    # virtual plane for phase space
    plane = sim.add_volume('Tubs', 'phase_space_plane')
    plane.mother = world.name
    plane.material = 'G4_AIR'
    plane.rmin = 0
    plane.rmax = 40 * mm
    plane.dz = 9 * cm  # half height
    plane.translation = [0, 0, -300 * mm - plane.dz]
    plane.color = [1, 0, 0, 1]  # red

    # e- source
    source = sim.add_source('Generic', 'Default')
    Bq = gam.g4_units('Bq')
    MeV = gam.g4_units('MeV')
    source.particle = 'e-'
    source.mother = f'{linac.name}_target'
    source.energy.type = 'gauss'
    source.energy.mono = 6.7 * MeV
    source.energy.sigma_gauss = 0.077 * MeV
    source.position.type = 'disc'
    source.position.radius = 2 * mm  # FIXME not really similar to GATE need sigma etc
    source.position.translation = [0, 0, 0.6 * mm]
    source.direction.type = 'momentum'
    source.direction.momentum = [0, 0, -1]
    source.activity = 5000 * Bq / ui.number_of_threads

    # add stat actor
    s = sim.add_actor('SimulationStatisticsActor', 'Stats')
    s.track_types_flag = True

    # PhaseSpace Actor
    ta2 = sim.add_actor('PhaseSpaceActor', 'PhaseSpace')
    ta2.mother = plane.name
    ta2.attributes = ['KineticEnergy', 'Weight', 'PostPosition', 'PrePosition', 'ParticleName',
                      'PreDirection', 'PostDirection', 'TimeFromBeginOfEvent',
                      'GlobalTime', 'LocalTime', 'EventPosition']
    ta2.output = paths.output / 'test019_hits.root'
    f = sim.add_filter('ParticleFilter', 'f')
    f.particle = 'gamma'
    ta2.filters.append(f)

    # phys
    p = sim.get_physics_user_info()
    p.physics_list_name = 'G4EmStandardPhysics_option4'
    p.enable_decay = False
    cuts = p.production_cuts
    cuts.world.gamma = 1 * mm
    cuts.world.electron = 1 * mm
    cuts.world.positron = 1 * mm

    return sim


def run_test019(sim):
    # create G4 objects
    sim.initialize()

    # splitting
    linac = sim.get_volume_user_info('linac')
    s = f'/process/em/setSecBiasing eBrem {linac.name}_target 100 100 MeV'
    print(s)
    sim.apply_g4_command(s)

    # start simulation
    sim.start()

    # print results
    stats = sim.get_actor('Stats')
    print(stats)

    h = sim.get_actor('PhaseSpace')
    print(h)

    """
    not done yet: 
    - missing several branch names in PhaseSpaceActor
    - no local/global for position
    - no policy options (all track single etc)
    - no MT yet 
    """

    # check stats
    print()
    stats_ref = gam.read_stat_file(paths.gate_output_ref / 'output-writePhS-stat.txt')
    print(f'Number of runs was {stats.counts.run_count}. Set to 1 before comparison')
    stats.counts.run_count = 1
    is_ok = gam.assert_stats(stats, stats_ref, 0.2)

    # compare the phsp tree
    print()
    fn1 = paths.gate_output_ref / 'output-PhS-g.root'
    fn2 = paths.output / 'test019_hits.root'
    print('Reference gate tree : ', fn1)
    print('Checked Tree : ', fn2)
    data_ref, keys_ref, m_ref = phsp.load(fn1)
    data, keys, m = phsp.load(fn2)
    # find the good key's names
    keys1, keys2, scalings, tols = gam.get_keys_correspondence(keys_ref)
    # Do not check some keys
    tols[keys1.index('Weight')] = 0.002
    tols[keys1.index('Z')] = 0.09
    tols[keys1.index('Ekine')] = 0.1
    tols[keys1.index('Y')] = 0.95
    tols[keys1.index('X')] = 1.2
    # the Z position is not the same (plane is translated), and is fixed
    mm = gam.g4_units('mm')
    data[:, keys.index('PostPosition_Z')] += 297 * mm
    # perform the test
    is_ok = gam.compare_trees(data_ref, keys_ref, data, keys, keys1, keys2, tols, scalings, True) and is_ok

    # figure
    plt.suptitle(f'Values: {len(data_ref)} vs {len(data)}')
    # plt.show()
    fn = paths.output / 'test019.png'
    plt.savefig(fn)
    print(f'Figure in {fn}')

    # this is the end, my friend
    gam.test_ok(is_ok)
