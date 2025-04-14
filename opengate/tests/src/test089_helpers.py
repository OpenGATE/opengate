#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test085_free_flight_helpers import *
import opengate.contrib.spect.siemens_intevo as intevo


def create_test089(sim, simu_name, visu=False):

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm

    # options
    sim.visu = visu
    sim.visu_type = "qt"
    sim.progress_bar = True
    sim.random_seed = "auto"
    sim.number_of_threads = 4

    # world and sect
    sim.world.size = [5 * m, 5 * m, 5 * m]
    sim.world.material = "G4_Galactic"
    radius = 28 * cm
    sa = [0, 180]
    crystals = []
    for i in range(2):
        det, colli, crystal = intevo.add_spect_head(sim, f"spect{i}", "melp")
        proj = intevo.add_intevo_digitizer_lu177_v3(sim, crystal.name, f"digit{i}")
        proj.output_filename = f"{simu_name}_{i}.mhd"
        proj.squared_counts.active = True
        intevo.rotate_gantry(det, radius, sa[i], 0, 1)
        crystals.append(crystal.name)
    print(crystals)

    # scatter volume
    wbox = sim.add_volume("BoxVolume", "waterbox")
    wbox.size = [30 * cm, 20 * cm, 30 * cm]
    wbox.material = "G4_WATER"
    wbox.color = [0, 0, 1, 1]

    # box sources
    box = sim.add_volume("BoxVolume", "box")
    box.mother = "waterbox"
    box.size = [0.2 * cm, 18 * cm, 0.2 * cm]
    box.translation = [-5 * cm, 0, 0]
    box.material = "G4_WATER"
    box.color = [1, 0, 0, 1]

    # change the source
    source = sim.add_source("GenericSource", "src")
    source.attached_to = "box"
    source.particle = "gamma"
    set_source_energy_spectrum(source, "lu177", "icrp107")
    source.position.type = "box"
    source.position.size = box.size
    source.direction.type = "iso"

    if sim.visu:
        sim.number_of_threads = 1
        source.activity = 1e3 * gate.g4_units.Bq

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.set_production_cut("world", "all", 1 * m)
    for crystal in crystals:
        sim.physics_manager.set_production_cut("world", crystal, 1 * mm)

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = f"{simu_name}_stats"

    # free flight actor
    s = f"/process/em/UseGeneralProcess false"
    sim.g4_commands_before_init.append(s)

    return stats, crystals, source
