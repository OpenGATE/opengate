#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, "gate_test043_garf", "test043")

m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
nm = gate.g4_units.nm
km = gate.g4_units.km
gcm3 = gate.g4_units.g_cm3
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
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
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1 * km


def sim_source_test(sim, activity):
    w, e = gate.sources.generic.get_rad_gamma_energy_spectrum("Tc99m")

    # first sphere
    s1 = sim.add_source("GenericSource", "s1")
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
    s2 = sim.add_source("GenericSource", "s2")
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
    s3 = sim.add_source("GenericSource", "s3")
    s3.particle = "gamma"
    s3.activity = activity
    s3.position.type = "sphere"
    s3.position.radius = 28 * mm
    s3.position.translation = [-10 * cm, 5 * cm, 0]
    s3.direction.type = "iso"
    s3.energy.type = "spectrum_lines"
    s3.energy.spectrum_energy = e
    s3.energy.spectrum_weight = w

    return s1, s2, s3


def create_sim_test_region(sim):
    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.number_of_threads = 1
    sim.visu = False
    sim.random_seed = 321654987

    # activity
    activity = 1e3 * Bq / sim.number_of_threads

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "GateMaterials.db")

    # init world
    sim_set_world(sim)

    # fake spect head
    head = gate_spect.add_fake_spect_head(sim, "spect")
    head.translation = [0, 0, -15 * cm]

    # detector input plane (+ 1nm to avoid overlap)
    pos, crystal_dist, psd = gate_spect.get_plane_position_and_distance_to_crystal(
        "lehr"
    )
    pos += 1 * nm
    print(f"plane position     {pos / mm} mm")
    print(f"crystal distance   {crystal_dist / mm} mm")
    detPlane = sim_add_detector_plane(sim, head.name, pos)

    sim.physics_manager.set_production_cut("world", "all", 1e3 * m)
    sim.physics_manager.set_production_cut("spect", "all", 1 * mm)

    # physics
    sim_phys(sim)

    # sources
    sim_source_test(sim, activity)

    # arf actor
    arf = sim.add_actor("ARFActor", "arf")
    arf.attached_to = detPlane.name
    arf.output_filename = paths.output / "test043_projection_garf.mhd"
    arf.batch_size = 2e5
    arf.image_size = [128, 128]
    arf.image_spacing = [4.41806 * mm, 4.41806 * mm]
    arf.verbose_batch = True
    arf.distance_to_crystal = crystal_dist  # 74.625 * mm
    arf.distance_to_crystal = 74.625 * mm
    arf.pth_filename = paths.gate_data / "pth" / "arf_Tc99m_v3.pth"
    arf.enable_hit_slice = True
    arf.gpu_mode = (
        utility.get_gpu_mode_for_tests()
    )  # should be "auto" but "cpu" for macOS github actions to avoid mps errors

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True
