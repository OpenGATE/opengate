#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#import itk
import uproot
import hist
import opengate as gate
#import xraylib
#import periodictable
from opengate.tests import utility
import os
import numpy as np
#import matplotlib.pyplot as plt
#import matplotlib.ticker as mticker
import test_088_variables


def simulation(output, File_name, job_id, number_of_particles, visu = False, verbose = False, actor = "VoxelizedPromptGammaTLEActor"):
    

    paths = utility.get_default_test_paths(__file__, output_folder=output)

    # create the simulation
    sim = gate.Simulation()
    # main options
    sim.visu = visu
    sim.g4_verbose = verbose
    sim.random_seed = "auto"  # FIXME to be replaced by a fixed number at the end
    sim.random_engine = "MersenneTwister"
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.progress_bar = True

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    m = gate.g4_units.m
    gcm3 = gate.g4_units.g_cm3
    keV = gate.g4_units.keV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    ns = gate.g4_units.ns
    mg = gate.g4_units.mg
    cm3 = gate.g4_units.cm3
    g = gate.g4_units.g
    km = gate.g4_units.km

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_Galactic"

    #cas test = boite à un élément
    ct = sim.add_volume("Box", "ct")
    ct.mother = "world"
    ct.translation = [0 * cm, 15 * cm, 0 * cm]
    ct.size = [4 * cm , 20 * cm , 4 * cm]
    ct.material = "G4_C"
    ct.color = [1, 0, 0, 1]

    """# insert voxelized CT
    ct = sim.add_volume("Image", "ct")
    ct.image = paths.data / f"ct_4mm.mhd"
    if sim.visu:
        ct.image = paths.data / f"ct_40mm.mhd"
    ct.material = "G4_AIR"
    f1 = str(paths.data / "Schneider2000MaterialsTable.txt")
    f2 = str(paths.data / "Schneider2000DensitiesTable.txt")
    tol = 0.05 * gcm3
    (
        ct.voxel_materials,
        materials,
    ) = gate.geometry.materials.HounsfieldUnit_to_material(sim, tol, f1, f2)
    print(f"tol = {tol/gcm3} g/cm3")
    print(f"mat : {len(ct.voxel_materials)} materials")

    ct.dump_label_image = paths.output / "labels.mhd" 
    ct.mother = "world"
    """


    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP_EMY"

    #sim.physics_manager.set_production_cut("world", "gamma", 1 * km) 
    #sim.physics_manager.set_production_cut("world", "electron", 1 * km) 
    #sim.physics_manager.set_production_cut("world", "proton", 1 * km) 
    #sim.physics_manager.set_production_cut("world", "positron", 1 * km) 

    sim.physics_manager.set_production_cut("ct", "gamma", 1 * mm) 
    #sim.physics_manager.set_production_cut("ct", "electron", 1 * mm) 
    sim.physics_manager.set_production_cut("ct", "proton", 1 * mm) 
    #sim.physics_manager.set_production_cut("ct", "positron", 1 * mm) 

    sim.physics_manager.set_max_step_size('ct', 1 * mm)
    sim.physics_manager.set_user_limits_particles(['proton'])


    # source of proton
    # FIXME to replace by a more realistic proton beam, see tests 044
    source = sim.add_source("GenericSource", "proton_beam")
    source.energy.mono = 150 * MeV
    source.particle = "proton"
    source.position.type = "disc"
    source.position.radius = 0
    source.position.translation = [0, 0, 0]
    source.n = number_of_particles
    source.direction.type = "momentum"
    source.direction.momentum = [0, 1, 0]


        #add vpgtle actor
    vpg_tle = sim.add_actor(actor, "vpg_tle")
    vpg_tle.attached_to = "ct"
    vpg_tle.output_filename = paths.output/f"{File_name}_appic_{job_id}.nii.gz"
    vpg_tle.size = [40, 400, 40]   
    vpg_tle.spacing = [1 * mm, 1 * mm, 1 * mm]
    vpg_tle.translation = [0, 0, 0]
    vpg_tle.timebins = 200
    vpg_tle.timerange = 1 * ns
    vpg_tle.energybins = 250
    vpg_tle.energyrange = 150 * MeV
    vpg_tle.prot_E.active = False

    vpg_tle.neutr_E.active =True
    vpg_tle.prot_tof.active = False
    vpg_tle.neutr_tof.active = True

     # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True
    stats.output_filename = paths.output/f"stat_{job_id}.txt"

    return sim, ct, vpg_tle, source


"""output = "TEST"
File_name = "test"
number_of_particles = 1000
actor = "VoxelizedPromptGammaTLEActor"

if __name__ == "__main__":
    sim = simulation(output, File_name, 0, number_of_particles,False, False, actor)
        # start simulation
    sim.run()"""

