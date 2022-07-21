#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam_gate as gam

paths = gam.get_default_test_paths(__file__, 'gate_test043_garf')

m = gam.g4_units('m')
cm = gam.g4_units('cm')
mm = gam.g4_units('mm')
nm = gam.g4_units('nm')
km = gam.g4_units('km')
gcm3 = gam.g4_units('g/cm3')
MeV = gam.g4_units('MeV')
keV = gam.g4_units('keV')
Bq = gam.g4_units('Bq')
kBq = 1000 * Bq


def sim_set_world(sim):
    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = 'G4_AIR'

    return world


def sim_set_detector_plane(sim, spect_name):
    # detector input plane
    detector_plane = sim.add_volume('Box', 'detPlane')
    detector_plane.mother = spect_name
    detector_plane.size = [57.6 * cm, 44.6 * cm, 1 * nm]
    """
    the detector is 'colli_trd' located in head, size and translation depends on the collimator type
    - lehr = 4.02 + 4.18 /2 = 6.13 + tiny shift (cm)
    - megp = 5.17 + 6.48 / 2.0 = 8.41 + tiny shift (cm)
    """
    # detector_plane.translation = [0, 0, 8.42 * cm]
    detector_plane.translation = [0, 0, 6.14 * cm]
    detector_plane.material = 'G4_Galactic'
    detector_plane.color = [1, 0, 0, 1]

    return detector_plane


def sim_phys(sim):
    p = sim.get_physics_user_info()
    p.physics_list_name = 'G4EmStandardPhysics_option4'
    sim.set_cut('world', 'all', 1 * km)


def sim_source_test(sim, volume_name, activity):
    # first sphere
    s1 = sim.add_source('Generic', 's1')
    s1.particle = 'gamma'
    s1.activity = activity * 0.0001
    s1.position.type = 'sphere'
    s1.position.radius = 15 * mm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = 'momentum'
    s1.direction.momentum = [0, 0, -1]
    # s1.direction.type = 'beam2d'
    s1.direction.sigma = [15 * mm, 15 * mm]
    s1.energy.type = 'spectrum'
    # Lu177
    # s1.energy.spectrum_energy = [0.0716418, 0.1129498, 0.1367245, 0.2083662, 0.2496742, 0.3213159]
    # s1.energy.spectrum_weight = [0.001726, 0.0620, 0.000470, 0.1038, 0.002012, 0.00216]
    # Tc99m
    s1.energy.spectrum_energy = [0.140511 * MeV]
    s1.energy.spectrum_weight = [0.885]

    # second sphere
    s2 = sim.add_source('Generic', 's2')
    s2.particle = 'gamma'
    s2.activity = activity
    s2.position.type = 'sphere'
    s2.position.radius = 15 * mm
    s2.position.translation = [15 * cm, 0, 0]
    s2.direction.type = 'iso'
    # s2.direction.type = 'momentum'
    # s2.direction.momentum = [0, 0, -1]
    # s2.direction.type = 'beam2d'
    # s2.direction.sigma = [25 * mm, 25 * mm]
    s2.energy.type = 'spectrum'
    s2.energy.spectrum_energy = s1.energy.spectrum_energy
    s2.energy.spectrum_weight = s1.energy.spectrum_weight
    # s2.direction.acceptance_angle.volumes = [volume_name]
    # s2.direction.acceptance_angle.intersection_flag = True

    # third sphere
    s3 = sim.add_source('Generic', 's3')
    s3.particle = 'gamma'
    s3.activity = activity
    s3.position.type = 'sphere'
    s3.position.radius = 28 * mm
    s3.position.translation = [-10 * cm, 5 * cm, 0]
    s3.direction.type = 'iso'
    # s3.direction.type = 'momentum'
    # s3.direction.momentum = [0, 0, -1]
    s3.energy.type = 'spectrum'
    s3.energy.spectrum_energy = s1.energy.spectrum_energy
    s3.energy.spectrum_weight = s1.energy.spectrum_weight
    #s3.direction.acceptance_angle.volumes = [volume_name]
    #s3.direction.acceptance_angle.intersection_flag = True
