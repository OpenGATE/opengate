#!/usr/bin/env python3
"""
Test and Guide: Intrinsic Activity in Detectors
-----------------------------------------------
This script demonstrates how to:
1. Define a PET scanner geometry with hierarchical volumes (Module -> Unit -> Block -> Crystal).
2. Define intrinsic activity (e.g., Lu176 background) confined specifically to the crystal volumes.
3. Calculate the total activity based on the volume of the crystals and a known concentration.
"""
import numpy as np
import opengate as gate
from opengate.geometry.utility import get_grid_repetition, get_circular_repetition

# ---------- units ----------
u = gate.g4_units
mm, cm = u.mm, u.cm
keV, Bq, sec = u.keV, u.Bq, u.s

# ---------- simulation/world and material ----------
sim = gate.Simulation()

sim.volume_manager.material_database.add_material_weights(
        "Vacuum", ["H"], [1], 1e-12 * u.g_cm3
    )

sim.volume_manager.material_database.add_material_weights(
    "LYSO", 
    ["Lu", "Y", "Si", "O"],     # Elements
    [0.714467891, 0.04033805, 0.063714272, 0.181479788],   # Mass Fractions (must sum to ~1.0)
    7.36 * u.g_cm3 # Density
)

sim.world.size = [90 * cm, 90 * cm, 90 * cm]
sim.world.material = "Vacuum"

sim.world.color = [1, 1, 1, 0]

# ---------- module container ----------
# Module: The main sector of the ring. Contains 5 Units in Z.
module = sim.add_volume("Box", "module")
module.mother = "world"
module.size = [64 * mm, 30 * mm, 180.0 * mm]
module.material = "Vacuum"
module.color = [1, 1, 1, 0]
translations_ring, rotations_ring = get_circular_repetition(
    20,
    [0 * mm, 300 * mm, 0 * mm],
    start_angle_deg=90,
    axis=[0, 0, 1]
)
module.translation = translations_ring
module.rotation = rotations_ring

# # ---------- Unit (1×5) inside Module ----------
Unit_det = sim.add_volume("Box", "Unit")
Unit_det.mother   = module.name
Unit_det.size     = [64 * mm, 30. * mm, 36 * mm]
Unit_det.material = "Vacuum"
Unit_det.color    = [1, 0, 0, 0]
Unit_det.translation = get_grid_repetition([1, 1, 5], [0 * mm, 0 * mm, 36 * mm])

# # ---------- Block (4×1) inside Unit ----------
Block_det = sim.add_volume("Box", "Block")
Block_det.mother   = Unit_det.name
Block_det.size     = [16 * mm, 30. * mm, 36 * mm]
Block_det.material = "Vacuum"
Block_det.color    = [0, 1, 0, 1]
Block_det.translation = get_grid_repetition([4, 1, 1], [16 * mm, 0.0 * mm, 0.0 * mm])

# # ---------- Crystal (4×9) inside Block ----------
crystal_det = sim.add_volume("Box", "crystal")
crystal_det.mother   = Block_det.name
crystal_det.size     = [4 * mm, 30. * mm, 4 * mm]
crystal_det.material = "Vacuum"
crystal_det.color    = [0, 0, 1, 0]
crystal_det.translation = get_grid_repetition([4, 1, 9], [4 * mm, 0.0 * mm, 4 * mm])

# # ---------- Crystal Layer (Active Material) same size as crystal_det ----------
# NOTE: This is the final layer of the geometry definition.
# It is defined as a single volume (no repetition here) inside the 'crystal' volume.
# We use THIS volume ('crystal_layer') for source confinement.
crystal_det_layer = sim.add_volume("Box", "crystal_layer")
crystal_det_layer.mother   = crystal_det.name
crystal_det_layer.size     = [4 * mm, 30. * mm, 4 * mm]
crystal_det_layer.material = "LYSO"
crystal_det_layer.color    = [0, 1, 1, 0]

# # ---------------------- Degitizer defination ----------------------
crystal_det_layer = sim.volume_manager.volumes["crystal_layer"]
Block_det = sim.volume_manager.volumes["Block"]

hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
hc.attached_to = crystal_det_layer.name
hc.authorize_repeated_volumes = True
hc.output_filename = None

hc.attributes = ['EventID', 'TrackID', 'TotalEnergyDeposit', 'GlobalTime', 'EventPosition',
                 'Position', 'ProcessDefinedStep', 'PostPosition', 'PreStepUniqueVolumeID']

sc = sim.add_actor("DigitizerReadoutActor", "Singles")
sc.input_digi_collection = "Hits"
sc.group_volume = Block_det.name
sc.discretize_volume = crystal_det_layer.name
sc.policy = "EnergyWeightedCentroidPosition"
sc.output_filename = r"singles.root"

# ---------------------- Change physics ----------------------
sim.physics_manager.physics_list_name = "G4EmPenelopePhysics"
sim.physics_manager.enable_decay = True

# ------------------ Intrinsic Activity Source ---------------------
# To simulate intrinsic activity (e.g., Lu176 in LYSO), we confine the source
# to the detector volume.

source_radius = 380.    # mm
source_hight = 255.     # mm
Lu176_concentration = 0.270     # Bq/mm3

# Calculate total volume of all crystals to determine total activity
# Volume = (Crystal Size) * (Crystals per Block) * (Blocks per Unit) * (Units per Module) * (Modules)
det_total_vol = (4 * 30. * 4) * (4 * 9) * 5 * 4 * 20   # mm3
total_activity = det_total_vol * Lu176_concentration

source = sim.add_source("GenericSource", "myConfSource")
# 'ion Z A' -> Lu is Z=71, Mass=176
source.particle = "ion 71 176"      # Lu176
source.position.type = "cylinder"
source.position.radius = source_radius * mm
source.position.dz = (source_hight / 2) * mm
source.position.translation = [0. * mm, 0. * mm, 0. * mm]
source.half_life = 3.7e10 * u.year
source.position.confine = crystal_det_layer.name
# Note: We confine to "crystal_layer". Since "crystal_layer" is inside repeated volumes
# (Block -> Unit -> Module), the source is automatically distributed across all instances.
# Activity is set for the *entire* confined volume name.
source.activity =  total_activity * Bq

stats = sim.add_actor("SimulationStatisticsActor", "Stats")
stats.track_types_flag = True
stats.output_filename = "stats.txt"


# ---------- Setup scan and viewer ----------
sim.g4_verbose = True
sim.g4_verbose_level = 1
sim.visu = False # True
# sim.visu_type = "vrml_file_only"    # "vrml"
# sim.visu_filename = "geometry.wrl"

sim.number_of_threads = 1

sim.random_engine = "MersenneTwister"
sim.random_seed = "auto"

sim.run_timing_intervals = [[0 * sec, 0.01 * sec]]

# ---------- Run ----------
# sim.run(start_new_process=True)   # not available on windows
sim.run()
