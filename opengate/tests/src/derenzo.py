### Derenzo phantom with 6 sets of cylinders of different size for each set
### For phantom1 set of cylinders each cylinder is assigned with an activity value
### The same procedure as in phantom1 with the activity can be followed to all phantom sets

import opengate as gate
from pathlib import Path
from opengate.geometry.materials import MaterialDatabase
import os
from scipy.spatial.transform import Rotation as R
from opengate.sources.utility import set_source_energy_spectrum
import math
import argparse
from opengate.voxelize import (
    voxelize_geometry,
    write_voxelized_geometry,
    voxelized_source,
)


# paths of the code
current_path = Path().resolve()  # actual current path of code
simulation_path = Path(current_path)
data_path = simulation_path / "data"
output_path = simulation_path / "output"


# define simulation inputs
materials = data_path / "GateMaterials1.db"


# Define the units used in the simulation set-up
m = gate.g4_units.m
cm = gate.g4_units.cm
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
mm = gate.g4_units.mm
sec = gate.g4_units.second
gcm3 = gate.g4_units.g_cm3
deg = gate.g4_units.deg
activity_1 = 2 * Bq
activity_2 = 2 * Bq
activities_1 = [2 * Bq, 5 * Bq, 10 * Bq]
activities_2 = [2 * Bq, 5 * Bq, 5 * Bq, 2 * Bq, 5 * Bq, 10 * Bq]
num_reps_1 = 3
num_reps_2 = 6


# Misc
yellow = [1, 1, 0, 0.5]
blue = [0, 0, 1, 0.5]
red = [1, 0, 0, 0.5]
white = [0, 0, 0, 0.5]
gray = [0.5, 0.5, 0.5, 1]
green = [0, 1, 0, 1]


if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    # Add a material database
    sim.volume_manager.add_material_database(data_path / "GateMaterials1.db")

    # Change world size
    world = sim.world
    world.size = [100 * cm, 100 * cm, 100 * cm]

    # Define the area around the derenzo
    area = sim.add_volume("Box", "area")
    area.size = [30 * cm, 30 * cm, 5 * cm]
    area.mother = "world"
    area.material = "G4_AIR"
    rot = R.from_euler("x", [-90], degrees=True)
    area.rotation = rot.as_matrix()

    # PHANTOM 1 (3 cylinders)
    phantom1 = sim.add_volume("Tubs", "phantom1")
    phantom1.material = "G4_WATER"
    phantom1.mother = "area"
    phantom1.rmin = 0 * mm
    phantom1.rmax = 14.5 * mm
    phantom1.dz = 12 * mm
    phantom1.color = yellow
    phantom1.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom1.translation = [
        [29 * mm, 105 * mm, 0],
        [-29 * mm, 105 * mm, 0],
        [0 * mm, 54.77 * mm, 0],
    ]
    print(f"The phantom1 is repeated in {phantom1.number_of_repetitions} locations. ")
    # print(f"Specified by the following translation vectors: ")
    # for i, t in enumerate(phantom1.translation):
    # 	print(f"Repetition {phantom1.get_repetition_name_from_index(i)}: {t}. ")

    ### Assign activity to all or separalety to each cylinder of the phantom1
    # for i in range (num_reps_1): ### if the activity is the same for all
    for i, act in enumerate(activities_1):  ### if the activity is different for all
        source_p1_rep = sim.add_source("GenericSource", f"phantom1_rep_{i}")
        source_p1_rep.particle = "gamma"
        # source_p1_rep.activity = activity_1  ### if the activity is the same for all
        source_p1_rep.activity = act  ### if the activity is different for all
        source_p1_rep.position.type = "point"
        source_p1_rep.direction.type = "iso"
        source_p1_rep.energy.mono = 140 * keV
        source_p1_rep.attached_to = phantom1.get_repetition_name_from_index(i)

    # PHANTOM 2 (6 cylinders)
    phantom2 = sim.add_volume("Tubs", "phantom2")
    phantom2.material = "G4_WATER"
    phantom2.mother = "area"
    phantom2.rmin = 0 * mm
    phantom2.rmax = 9.3 * mm
    phantom2.dz = 12 * mm
    phantom2.color = yellow
    phantom2.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom2.translation = [
        [66 * mm, 25 * mm, 0],
        [66 * mm, 89.44 * mm, 0],
        [28.8 * mm, 25 * mm, 0],
        [103.2 * mm, 25 * mm, 0],
        [84.5 * mm, 57.21 * mm, 0],
        [47.5 * mm, 57.21 * mm, 0],
    ]
    print(f"The phantom2 is repeated in {phantom2.number_of_repetitions} locations. ")

    ### Assign activity to all or separalety to each cylinder of the phantom2
    # for i in range (num_reps_2): ### if the activity is the same for all
    for i, act in enumerate(activities_2):  ### if the activity is different for all
        source_p2_rep = sim.add_source("GenericSource", f"phantom2_rep_{i}")
        source_p2_rep.particle = "gamma"
        # source_p2_rep.activity = activity_2  ### if the activity is the same for all
        source_p2_rep.activity = act  ### if the activity is different for all
        source_p2_rep.position.type = "point"
        source_p2_rep.direction.type = "iso"
        source_p2_rep.energy.mono = 140 * keV
        source_p2_rep.attached_to = phantom2.get_repetition_name_from_index(i)

    # PHANTOM 3 (10 cylinders)
    phantom3 = sim.add_volume("Tubs", "phantom3")
    phantom3.material = "G4_WATER"
    phantom3.mother = "area"
    phantom3.rmin = 0 * mm
    phantom3.rmax = 7.85 * mm
    phantom3.dz = 12 * mm
    phantom3.color = yellow
    phantom3.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom3.translation = [
        [66 * mm, -45.19 * mm, 0],
        [97.4 * mm, -45.19 * mm, 0],
        [34.6 * mm, -45.19 * mm, 0],
        [18.9 * mm, -18 * mm, 0],
        [50.3 * mm, -18 * mm, 0],
        [81.7 * mm, -18 * mm, 0],
        [113.1 * mm, -18 * mm, 0],
        [50.3 * mm, -72.38 * mm, 0],
        [81.7 * mm, -72.38 * mm, 0],
        [66 * mm, -99.57 * mm, 0],
    ]
    print(f"The phantom3 is repeated in {phantom3.number_of_repetitions} locations. ")

    # PHANTOM 4 (10 cylinders)
    phantom4 = sim.add_volume("Tubs", "phantom4")
    phantom4.material = "G4_WATER"
    phantom4.mother = "area"
    phantom4.rmin = 0 * mm
    phantom4.rmax = 6.5 * mm
    phantom4.dz = 12 * mm
    phantom4.color = yellow
    phantom4.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom4.translation = [
        [0 * mm, -91.69 * mm, 0],
        [0 * mm, -46.67 * mm, 0],
        [26 * mm, -91.69 * mm, 0],
        [-26 * mm, -91.69 * mm, 0],
        [-13 * mm, -69.18 * mm, 0],
        [13 * mm, -69.18 * mm, 0],
        [13 * mm, -114.2 * mm, 0],
        [-13 * mm, -114.2 * mm, 0],
        [-39 * mm, -114.2 * mm, 0],
        [39 * mm, -114.2 * mm, 0],
    ]
    print(f"The phantom4 is repeated in {phantom4.number_of_repetitions} locations. ")

    # PHANTOM 5 (10 cylinders)
    phantom5 = sim.add_volume("Tubs", "phantom5")
    phantom5.material = "G4_WATER"
    phantom5.mother = "area"
    phantom5.rmin = 0 * mm
    phantom5.rmax = 5.75 * mm
    phantom5.dz = 12 * mm
    phantom5.color = yellow
    phantom5.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom5.translation = [
        [-66 * mm, -42.92 * mm, 0],
        [-89 * mm, -42.92 * mm, 0],
        [-43 * mm, -42.92 * mm, 0],
        [-66 * mm, -82.76 * mm, 0],
        [-54.5 * mm, -62.84 * mm, 0],
        [-77.5 * mm, -62.84 * mm, 0],
        [-54.5 * mm, -23 * mm, 0],
        [-77.5 * mm, -23 * mm, 0],
        [-31.5 * mm, -23 * mm, 0],
        [-100.5 * mm, -23 * mm, 0],
    ]
    print(f"The phantom5 is repeated in {phantom5.number_of_repetitions} locations. ")

    # PHANTOM 6 (15 cylinders)
    phantom6 = sim.add_volume("Tubs", "phantom6")
    phantom6.material = "G4_WATER"
    phantom6.mother = "area"
    phantom6.rmin = 0 * mm
    phantom6.rmax = 5 * mm
    phantom6.dz = 12 * mm
    phantom6.color = yellow
    phantom6.translation = [29 * mm, 1.5 * mm, 105 * mm]
    m = R.identity().as_matrix()
    phantom6.translation = [
        [-66 * mm, 17 * mm, 0],
        [-46 * mm, 17 * mm, 0],
        [-26 * mm, 17 * mm, 0],
        [-86 * mm, 17 * mm, 0],
        [-106 * mm, 17 * mm, 0],
        [-56 * mm, 34.32 * mm, 0],
        [-36 * mm, 34.32 * mm, 0],
        [-76 * mm, 34.32 * mm, 0],
        [-96 * mm, 34.32 * mm, 0],
        [-66 * mm, 51.64 * mm, 0],
        [-46 * mm, 51.64 * mm, 0],
        [-86 * mm, 51.64 * mm, 0],
        [-76 * mm, 68.96 * mm, 0],
        [-56 * mm, 68.96 * mm, 0],
        [-66 * mm, 86.28 * mm, 0],
    ]
    print(f"The phantom6 is repeated in {phantom6.number_of_repetitions} locations. ")

    # PHYSICS
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = True

    # ACQUISITION
    sim.check_volumes_overlap = True
    sim.g4_verbose = True
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = "vrml"
    # sim.visu_verbose = True
    # sim.progress_bar = True
    sim.number_of_threads = 1
    # sim.output_dir = "output"
    # source.n = 10000000

    # run
    sim.run()
