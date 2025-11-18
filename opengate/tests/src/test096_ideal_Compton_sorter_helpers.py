#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Simulation to test the ideal sorter to recover Compton kinematics

import opengate as gate
from opengate.tests import utility

# colors
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]


def create_and_run_cc_simulation():
    paths = utility.get_default_test_paths(__file__, "gate_test096", "test096")

    sim = gate.Simulation()

    # options
    sim.visu = False
    sim.visu_type = "vrml"
    sim.random_seed = "auto"
    sim.number_of_threads = 1

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    gcm3 = gate.g4_units.g_cm3
    sec = gate.g4_units.s

    # folders
    output_path = paths.output
    sim.output_dir = output_path

    sim.volume_manager.material_database.add_material_weights(
        "LYSO",
        ["Lu", "Y", "Si", "O", "Ce"],
        [
            0.713838658203075,
            0.040302477781781,
            0.063721807284236,
            0.181501252152072,
            0.000635804578835201,
        ],
        7.10 * gcm3,
    )

    # world
    world = sim.world
    world.size = [10 * cm, 10 * cm, 40 * cm]
    # sim.world.material = "G4_AIR"
    sim.world.material = "G4_Galactic"

    # BB box for CCMod actor is not needed anymore ?
    BB = sim.add_volume("Box", "BB_box")
    BB.mother = sim.world
    # BB.material = "G4_AIR"
    BB.material = "G4_Galactic"
    BB.size = [4 * cm, 4 * cm, 7.6 * cm]
    BB.translation = [0, 0, 8.3 * cm]
    BB.color = [1, 0, 0, 1]  # red

    # Scatt
    Scatt = sim.add_volume("Box", "scatt_box")
    Scatt.mother = BB.name
    Scatt.material = "LYSO"
    Scatt.size = [2.72 * cm, 2.68 * cm, 0.5 * cm]
    Scatt.translation = [0, 0, -2.75 * cm]

    # Absorber
    Abs = sim.add_volume("Box", "Abs_box")
    Abs.mother = BB.name
    Abs.material = "LYSO"
    Abs.size = [3.24 * cm, 3.6 * cm, 1.0 * cm]
    Abs.translation = [0, 0, 2.5 * cm]

    # stats
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "stats.txt"

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta2.attached_to = BB.name
    ta2.attributes = [
        "TotalEnergyDeposit",
        "PreKineticEnergy",
        "PostKineticEnergy",
        "PostPosition",
        "ProcessDefinedStep",
        # "ParticleName",
        "EventID",
        "ParentID",
        "PDGCode",
        # "TrackVertexKineticEnergy",
        "GlobalTime",
    ]
    ta2.output_filename = output_path / "PhaseSpace.root"
    ta2.steps_to_store = "allsteps"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    ta2.filters.append(f)

    # check overlap
    sim.check_volumes_overlap = True

    # phys
    sim.physics_manager.physics_list_name = (
        "G4EmStandardPhysics_option2"  # To avoid Doppler
    )
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)
    sim.physics_manager.set_production_cut("BB_box", "all", 0.1 * mm)

    # source
    source = sim.add_source("GenericSource", "src")
    source.particle = "gamma"
    source.energy.mono = 662 * keV
    source.position.type = "sphere"
    source.position.radius = 0.25 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.activity = 0.847 * 1e6 * Bq / sim.number_of_threads

    if sim.visu:
        source.activity = 1 * Bq

    # timing
    sim.run_timing_intervals = [[0, 5 * sec]]

    # go
    sim.run()

    # end
    print(stats)
