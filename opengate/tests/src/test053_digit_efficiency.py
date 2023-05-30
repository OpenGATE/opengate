#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate_core as g4

paths = gate.get_default_test_paths(__file__, "gate_test053_digit_efficiency")

"""
PET simulation to test efficiency options of the digitizer

- output: singles with and without decreased efficiency
"""

sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.visu = False
ui.number_of_threads = 1
ui.check_volumes_overlap = False

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
keV = gate.g4_units("keV")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")

# world size
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]

# material
sim.add_material_database(paths.data / "GateMaterials.db")

# crystal
crystal = sim.add_volume("Box", "crystal")
crystal.mother = "SPECThead"
crystal.size = [1.0 * cm, 1.0 * cm, 1.0 * cm]
crystal.material = "NaITl"
start = [-25 * cm, -20 * cm, 4 * cm]
size = [100, 40, 1]
# size = [100, 80, 1]
tr = [0.5 * cm, 0.5 * cm, 0]
crystal.repeat = gate.repeat_array_start("crystal1", start, size, tr)
crystal.color = [1, 1, 0, 1]

# physic list
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
p.enable_decay = False
cuts = p.production_cuts
cuts.world.gamma = 0.01 * mm
cuts.world.electron = 0.01 * mm
cuts.world.positron = 1 * mm
cuts.world.proton = 1 * mm

# default source for tests
source = sim.add_source("GenericSource", "Default")
source.particle = "gamma"
source.energy.mono = 140.5 * keV
source.position.type = "sphere"
source.position.radius = 4 * cm
source.position.translation = [0, 0, -15 * cm]
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.activity = 50000 * Bq / ui.number_of_threads

# add stat actor
sim.add_actor("SimulationStatisticsActor", "Stats")

# print list of attributes
am = g4.GateDigiAttributeManager.GetInstance()
print(am.GetAvailableDigiAttributeNames())

# hits collection
hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
hc.mother = [crystal.name, crystal2.name]
mt = ""
if ui.number_of_threads > 1:
    mt = "_MT"
hc.output = paths.output / ("test025_hits" + mt + ".root")
hc.attributes = [
    "TotalEnergyDeposit",
    "KineticEnergy",
    "PostPosition",
    "TrackCreatorProcess",
    "GlobalTime",
    "TrackVolumeName",
    "RunID",
    "ThreadID",
    "TrackID",
]

sim.start()

# ----------------------------------------------------------------------------------------------------------
