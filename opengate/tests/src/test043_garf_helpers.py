#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "gate_test043_garf")

m = gate.g4_units("m")
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
nm = gate.g4_units("nm")
km = gate.g4_units("km")
gcm3 = gate.g4_units("g/cm3")
MeV = gate.g4_units("MeV")
keV = gate.g4_units("keV")
Bq = gate.g4_units("Bq")
kBq = 1000 * Bq


def sim_set_world(sim):
    # world size
    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_AIR"

    return world


def sim_add_detector_plane(sim, spect_name, distance, plane_name="detPlane"):
    # detector input plane
    detector_plane = sim.add_volume("Box", plane_name)
    detector_plane.mother = spect_name
    detector_plane.size = [57.6 * cm, 44.6 * cm, 1 * nm]
    detector_plane.translation = [0, 0, distance]
    detector_plane.material = "G4_Galactic"
    detector_plane.color = [0, 1, 0, 1]

    return detector_plane


def sim_phys(sim):
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    sim.set_cut("world", "all", 1 * km)


def sim_source_test(sim, activity):
    w, e = gate.get_rad_gamma_energy_spectrum("Tc99m")

    # first sphere
    s1 = sim.add_source("Generic", "s1")
    s1.particle = "gamma"
    s1.activity = activity * 0.0001
    s1.position.type = "sphere"
    s1.position.radius = 15 * mm
    s1.position.translation = [0, 0, 0]
    s1.direction.type = "momentum"
    s1.direction.momentum = [0, 0, -1]
    s1.energy.type = "spectrum_lines"
    s1.energy.spectrum_energy = e
    s1.energy.spectrum_weight = w

    # second sphere
    s2 = sim.add_source("Generic", "s2")
    s2.particle = "gamma"
    s2.activity = activity * 2
    s2.position.type = "sphere"
    s2.position.radius = 15 * mm
    s2.position.translation = [15 * cm, 0, 0]
    s2.direction.type = "iso"
    s2.energy.type = "spectrum_lines"
    s2.energy.spectrum_energy = e
    s2.energy.spectrum_weight = w

    # third sphere
    s3 = sim.add_source("Generic", "s3")
    s3.particle = "gamma"
    s3.activity = activity
    s3.position.type = "sphere"
    s3.position.radius = 28 * mm
    s3.position.translation = [-10 * cm, 5 * cm, 0]
    s3.direction.type = "iso"
    s3.energy.type = "spectrum_lines"
    s3.energy.spectrum_energy = e
    s3.energy.spectrum_weight = w
