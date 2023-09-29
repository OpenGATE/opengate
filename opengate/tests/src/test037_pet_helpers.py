#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.pet.philipsvereos as pet_vereos
import opengate.contrib.phantoms.necr as phantom_necr

from opengate.userhooks import check_production_cuts


def make_simu(sim=None, output_path="./"):
    # create the simulation
    if sim is None:
        sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.check_volumes_overlap = False

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm
    Bq = gate.g4_units.Bq
    MBq = Bq * 1e6
    sec = gate.g4_units.second

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # add a PET VEREOS
    pet = pet_vereos.add_pet(sim, "pet")

    # add table
    bed = pet_vereos.add_table(sim, "pet")

    # add NECR phantom
    phantom = phantom_necr.add_necr_phantom(sim, "phantom")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.set_production_cut("world", "all", 1 * m)

    reg1 = sim.add_region("reg1")
    reg1.production_cuts.all = 0.1 * mm
    reg1.associate_volume(phantom)
    reg1.associate_volume(bed)
    reg1.associate_volume(f"{pet.name}_crystal")
    # sim.set_production_cut(phantom.name, "all", 0.1 * mm)
    # sim.set_production_cut(bed.name, "all", 0.1 * mm)
    # sim.set_production_cut(f"{pet.name}_crystal", "all", 0.1 * mm)

    # default source for tests
    source = phantom_necr.add_necr_source(sim, phantom)
    total_yield = gate.sources.generic.get_rad_yield("F18")
    print("Yield for F18 (nb of e+ per decay) : ", total_yield)
    source.activity = 3000 * Bq * total_yield
    source.activity = 1787.914158 * MBq * total_yield
    source.half_life = 6586.26 * sec
    source.energy.type = "F18_analytic"  # FIXME not ok, but similar to previous Gate

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    # get crystal volume by looking for the word crystal in the name
    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    hc.mother = crystal.name
    print("Crystal :", crystal.name)
    hc.output = output_path / "test037_test1.root"
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "TrackVolumeCopyNo",
        "PostStepUniqueVolumeID",
        "PreStepUniqueVolumeID",
        "GlobalTime",
        # "KineticEnergy", # not needed
        # "ProcessDefinedStep", # not needed
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.mother = crystal.name
    sc.input_digi_collection = "Hits"
    # sc.policy = "EnergyWinnerPosition"
    sc.policy = "EnergyWeightedCentroidPosition"
    # the following attributes is not needed in singles
    # sc.skip_attributes = ["KineticEnergy"]
    sc.output = hc.output

    # add user hook function to dump production cuts from G4
    sim.user_fct_after_init = check_production_cuts

    # timing
    sim.run_timing_intervals = [[0, 0.0002 * sec]]
