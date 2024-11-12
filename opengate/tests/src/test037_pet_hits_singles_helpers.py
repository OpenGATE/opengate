#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.pet.philipsvereos as pet_vereos
import opengate.contrib.phantoms.necr as phantom_necr
from opengate.tests import utility
from opengate.userhooks import check_production_cuts


def create_pet_simulation(sim, paths, debug=False, create_mat=False):
    """
    Simulation of a PET VEREOS with NEMA NECR phantom.
    - phantom is a simple cylinder and linear source
    - output is hits and singles only (no coincidences)
    - also digitizer is simplified: only raw hits and adder (for singles)
    """

    # main options
    sim.g4_verbose = False
    sim.visu = False
    sim.check_volumes_overlap = False
    sim.random_seed = 123456789
    sim.output_dir = paths.output

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    MBq = Bq * 1e6
    sec = gate.g4_units.second

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # add a PET VEREOS
    sim.volume_manager.add_material_database(paths.gate_data / "GateMaterials_pet.db")
    if not debug:
        pet = pet_vereos.add_pet(sim, "pet", create_housing=True, create_mat=create_mat)
    else:
        pet = pet_vereos.add_pet(
            sim, "pet", create_housing=True, create_mat=create_mat, debug=True
        )

    # add table
    bed = pet_vereos.add_table(sim, "pet")

    # add NECR phantom
    phantom = phantom_necr.add_necr_phantom(sim, "phantom")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 1 * m)

    reg1 = sim.physics_manager.add_region("reg1")
    reg1.production_cuts.all = 10 * mm
    reg1.associate_volume(phantom)
    reg1.associate_volume(bed)

    reg2 = sim.physics_manager.add_region("reg2")
    reg2.production_cuts.all = 0.1 * mm
    reg2.associate_volume(f"{pet.name}_crystal")

    # default source for tests
    source = phantom_necr.add_necr_source(sim, phantom)
    total_yield = gate.sources.generic.get_rad_yield("F18")
    print("Yield for F18 (nb of e+ per decay) : ", total_yield)
    source.activity = 3000 * Bq * total_yield
    source.activity = 1787.914158 * MBq * total_yield
    source.half_life = 6586.26 * sec
    source.energy.type = "F18_analytic"  # WARNING not ok, but similar to previous Gate
    # source.energy.type = "F18"  # this is the correct F18 e+ source

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # set user hook function
    sim.user_hook_after_init = check_production_cuts

    for vol in sim.volume_manager.volumes.values():
        if "crystal" in vol.name:
            return vol
    gate.exception.fatal("Could not find any crystal volume.")


def add_digitizer(sim, paths, nb, crystal):
    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.attached_to = crystal.name
    hc.authorize_repeated_volumes = True
    print("Crystal :", crystal.name)
    hc.output_filename = f"test037_test{nb}.root"
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # singles collection
    sc = sim.add_actor("DigitizerAdderActor", "Singles")
    sc.input_digi_collection = "Hits"
    # sc.policy = "EnergyWinnerPosition"
    sc.policy = "EnergyWeightedCentroidPosition"
    sc.output_filename = hc.output_filename

    return sim


def default_root_hits_branches():
    k1 = ["posX", "posY", "posZ", "edep", "time"]
    k2 = [
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
        "TotalEnergyDeposit",
        "GlobalTime",
    ]
    return k1, k2


def default_root_singles_branches():
    k1 = ["globalPosX", "globalPosY", "globalPosZ", "energy", "time"]
    k2 = [
        "PostPosition_X",
        "PostPosition_Y",
        "PostPosition_Z",
        "TotalEnergyDeposit",
        "GlobalTime",
    ]
    return k1, k2


def check_root_hits(paths, nb, ref_hits_output, hits_output, png_output="auto"):
    if png_output == "auto":
        png_output = f"test037_test{nb}_hits.png"
    # check phsp (new version)
    print()
    gate.exception.warning(f"Check root (hits)")
    k1, k2 = default_root_hits_branches()
    p1 = utility.root_compare_param_tree(ref_hits_output, "Hits", k1)
    # in the legacy gate, some edep=0 are still saved in the root file,
    # so we don't count that ones in the histogram comparison
    p1.mins[k1.index("edep")] = 0
    p2 = utility.root_compare_param_tree(hits_output, "Hits", k2)
    p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p = utility.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 6  # % tolerance (including the edep zeros)
    p.tols[k1.index("posX")] = 10
    p.tols[k1.index("posY")] = 10
    p.tols[k1.index("posZ")] = 1.5
    p.tols[k1.index("edep")] = 0.002
    p.tols[k1.index("time")] = 0.0001
    is_ok = utility.root_compare4(p1, p2, p)

    return is_ok


def check_root_singles(
    paths, v, ref_singles_output, singles_output, sname="Singles", png_output="auto"
):
    if png_output == "auto":
        png_output = f"test037_test{v}_singles.png"
    # check phsp (singles)
    print()
    gate.exception.warning(f"Check root (singles)")
    k1, k2 = default_root_singles_branches()
    p1 = utility.root_compare_param_tree(ref_singles_output, "Singles", k1)
    # in the legacy gate, some edep=0 are still saved in the root file,
    # so we don't count that ones in the histogram comparison
    p1.mins[k1.index("energy")] = 0
    p2 = utility.root_compare_param_tree(singles_output, sname, k2)
    p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p = utility.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 5  # % tolerance (including the edep zeros)
    p.tols[k1.index("globalPosX")] = 5
    p.tols[k1.index("globalPosY")] = 5
    p.tols[k1.index("globalPosZ")] = 1.5
    p.tols[k1.index("energy")] = 0.0045
    p.tols[k1.index("time")] = 0.0001

    is_ok = utility.root_compare4(p1, p2, p)

    return is_ok
