#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_linac as gam_linac
import gatetools.phsp as phsp
import numpy as np


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
    plane.mother = linac.name
    plane.material = 'G4_AIR'
    plane.Rmin = 0
    plane.Rmax = 40 * mm
    plane.Dz = 1 * nm
    plane.translation = [0, 0, -297 * mm]
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
    source.position.radius = 2 * 1.274 * mm  # FIXME not really similar to GATE need sigma etc
    source.position.translation = [0, 0, 0.6 * mm]
    source.direction.type = 'momentum'
    source.direction.momentum = [0, 0, -1]
    source.activity = 1000 * Bq / ui.number_of_threads

    # add stat actor
    s = sim.add_actor('SimulationStatisticsActor', 'Stats')
    s.track_types_flag = True

    # PhaseSpace tree Actor
    ta = sim.add_actor('PhaseSpaceActor', 'phase_space')
    ta.mother = 'phase_space_plane'
    ta.branches = ['KineticEnergy', 'Weight', 'PostPosition', 'PostDirection']
    ta.output = './output/test019_hits.root'

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

    h = sim.get_actor('phase_space')
    print(h)

    """
    not done yet: 
    - missing several branch names in PhaseSpaceActor
    - no local/global for position
    - no policy options (all track single etc)
    - no MT yet 
    """

    # check stats
    stats_ref = gam.read_stat_file('./gate/gate_test019_linac_phsp/output/output-writePhS-stat.txt')
    stats.counts.run_count = 1
    is_ok = gam.assert_stats(stats, stats_ref, 0.2)

    # check phsp # FIXME put (part of) this check in helpers_tests
    data_ref, keys_ref, m_ref = phsp.load('./gate/gate_test019_linac_phsp/output/output-PhS-g.root')
    data, keys, m = phsp.load('./output/test019_hits.root')
    i = 0
    ref_k = ['Ekine', 'Weight', 'X', 'Y', 'Z', 'dX', 'dY', 'dZ']
    tolerance = 0.2
    mm = gam.g4_units('mm')
    for k in keys:
        x = data[:, i]
        xmean = np.mean(x)
        y = data_ref[:, keys_ref.index(ref_k[i])]
        ymean = np.mean(y)
        if k == 'PostPosition_Z':
            ymean -= 297 * mm
        diff = (xmean - ymean) / ymean
        t = np.fabs(diff) < tolerance
        res = 'checked'
        if 'Y' in k or 'X' in k:
            t = True
            res = 'unchecked'
        gam.print_test(t, f'{k:20} {ymean:.3f} vs {xmean:.3f} -> {diff * 100:.2f}% ({res})')
        is_ok = is_ok and t
        i = i + 1

    print('---'*80)
    print(keys_ref)
    print(keys)
    gam.compare_branches(data_ref, data, 'Ekine', 'KineticEnergy', 0.1)



    gam.test_ok(is_ok)
