#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from test013_phys_lists_helpers import create_pl_sim

paths = utility.get_default_test_paths(__file__, "")

# create simulation
sim = gate.Simulation()
ui = sim.user_info
ui.g4_verbose = True

# units
m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
eV = gate.g4_units.eV
MeV = gate.g4_units.MeV
Bq = gate.g4_units.Bq

# add a material database
sim.add_material_database(paths.data / "GateMaterials.db")

# set the world size like in the Gate macro
world = sim.world
world.size = [3 * m, 3 * m, 3 * m] 

# add a simple waterbox volume
waterbox = sim.add_volume("Box", "waterbox")
waterbox.size = [2 * cm, 2 * cm, 2 * cm]
waterbox.translation = [0 * cm, 0 * cm, 0 * cm]
waterbox.material = "BGO"

# change physics
sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
sim.physics_manager.energy_range_min = 10 * eV
sim.physics_manager.energy_range_max = 1 * MeV
sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True

# Change source
source = sim.add_source("GenericSource", "gamma1")
source.particle = "gamma"
source.energy.mono = 0.511 * MeV
source.activity = 100 * Bq
source.direction.type = "momentum"
source.direction.momentum = [0, 0, -1]
source.position.translation = [0 * cm, 0 * cm, 2.2 * cm]

#add phase actor 
phase = sim.add_actor("PhaseSpaceActor", "Phase")
phase.mother = waterbox.name
phase.attributes = [
    "Position",
    "PostPosition",
    "PrePosition",
    "ParticleName",
    "TrackCreatorProcess",
    # 'TrackVertexKineticEnergy', 'EventKineticEnergy'
]
phase.output = paths.output / "test057_phys_lists_6.root"

sim.run()
