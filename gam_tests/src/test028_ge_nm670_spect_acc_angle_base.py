#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam
import contrib.gam_ge_nm670_spect as gam_spect


def create_spect_simu(sim, paths, number_of_threads=1, activity_kBq=300):
    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.number_of_threads = number_of_threads
    ui.check_volumes_overlap = False

    # units
    m = gam.g4_units('m')
    cm = gam.g4_units('cm')
    keV = gam.g4_units('keV')
    mm = gam.g4_units('mm')
    Bq = gam.g4_units('Bq')
    kBq = 1000 * Bq

    # world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = 'G4_AIR'

    # spect head (debug mode = very small collimator)
    spect = gam_spect.add_spect(sim, 'spect', collimator=True, debug=False)

    # waterbox
    waterbox = sim.add_volume('Box', 'waterbox')
    waterbox.size = [15 * cm, 15 * cm, 15 * cm]
    waterbox.material = 'G4_WATER'
    waterbox.translation = [0, 0, 0]
    blue = [0, 1, 1, 1]
    waterbox.color = blue

    # physic list
    p = sim.get_physics_user_info()
    p.physics_list_name = 'G4EmStandardPhysics_option4'
    p.enable_decay = False
    cuts = p.production_cuts
    cuts.world.gamma = 10 * mm
    cuts.world.electron = 10 * mm
    cuts.world.positron = 10 * mm
    cuts.world.proton = 10 * mm
    cuts.spect.gamma = 0.1 * mm
    cuts.spect.electron = 0.1 * mm
    cuts.spect.positron = 0.1 * mm

    # default source for tests
    # activity = 300 * kBq
    activity = activity_kBq * kBq
    beam1 = sim.add_source('Generic', 'beam1')
    beam1.mother = waterbox.name
    beam1.particle = 'gamma'
    beam1.energy.mono = 140.5 * keV
    beam1.position.type = 'sphere'
    beam1.position.radius = 1 * cm
    beam1.position.translation = [0, 0, 0]
    beam1.direction.type = 'momentum'
    beam1.direction.momentum = [0, 0, -1]
    beam1.direction.type = 'iso'
    beam1.direction.angle_acceptance_volume = 'spect'
    beam1.activity = activity / ui.number_of_threads

    beam2 = sim.add_source('Generic', 'beam2')
    beam2.mother = waterbox.name
    beam2.particle = 'gamma'
    beam2.energy.mono = 140.5 * keV
    beam2.position.type = 'sphere'
    beam2.position.radius = 3 * cm
    beam2.position.translation = [18 * cm, 0, 0]
    # beam2.direction.type = 'momentum'
    beam2.direction.type = 'iso'
    beam2.direction.angle_acceptance_volume = 'spect'
    beam2.activity = activity / ui.number_of_threads

    beam3 = sim.add_source('Generic', 'beam3')
    beam3.mother = waterbox.name
    beam3.particle = 'gamma'
    beam3.energy.mono = 140.5 * keV
    beam3.position.type = 'sphere'
    beam3.position.radius = 1 * cm
    beam3.position.translation = [0, 10 * cm, 0]
    # beam3.direction.type = 'momentum'
    beam3.direction.type = 'iso'
    beam3.direction.angle_acceptance_volume = 'spect'
    beam3.activity = activity / ui.number_of_threads

    # add stat actor
    sim.add_actor('SimulationStatisticsActor', 'Stats')

    # hits collection
    hc = sim.add_actor('HitsCollectionActor', 'Hits')
    # get crystal volume by looking for the word crystal in the name
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if 'crystal' in k][0]]
    hc.mother = crystal.name
    hc.output = ''  # No output paths.output / 'test028.root'
    hc.attributes = ['PostPosition', 'TotalEnergyDeposit']

    # singles collection
    sc = sim.add_actor('HitsAdderActor', 'Singles')
    sc.mother = crystal.name
    sc.input_hits_collection = 'Hits'
    sc.policy = 'TakeEnergyWinner'
    # sc.policy = 'TakeEnergyCentroid'
    sc.skip_attributes = ['KineticEnergy', 'ProcessDefinedStep', 'KineticEnergy']
    sc.output = hc.output

    # EnergyWindows
    cc = sim.add_actor('HitsEnergyWindowsActor', 'EnergyWindows')
    cc.mother = crystal.name
    cc.input_hits_collection = 'Singles'
    cc.channels = [{'name': 'scatter', 'min': 114 * keV, 'max': 126 * keV},
                   {'name': 'peak140', 'min': 126 * keV, 'max': 154.55 * keV},
                   # {'name': 'spectrum', 'min': 0 * keV, 'max': 5000 * keV}  # should be strictly equal to 'Singles'
                   ]
    cc.output = hc.output

    # sec = gam.g4_units('second')
    # sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1 * sec]]

    # projection
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if 'crystal' in k][0]]
    # 2D binning projection
    proj = sim.add_actor('HitsProjectionActor', 'Projection')
    proj.mother = crystal.name
    # we set two times the spectrum channel to compare with Gate output
    proj.input_hits_collections = ['Singles', 'scatter', 'peak140', 'Singles']
    proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.dimension = [128, 128]
    # proj.plane = 'XY' # not implemented yet
    proj.output = paths.output / 'proj028_colli.mhd'

    return spect, proj
