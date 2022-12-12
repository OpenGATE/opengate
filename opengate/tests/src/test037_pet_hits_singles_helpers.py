#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.pet_philips_vereos as pet_vereos
import opengate.contrib.phantom_necr as phantom_necr


def create_pet_simulation(sim, paths):
    """
    Simulation of a PET VEREOS with NEMA NECR phantom.
    - phantom is a simple cylinder and linear source
    - output is hits and singles only (no coincidences)
    - also digitizer is simplified: only raw hits and adder (for singles)
    """

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.visu = False
    ui.check_volumes_overlap = False
    ui.random_seed = 123456789

    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    MBq = Bq * 1e6
    sec = gate.g4_units("second")

    #  change world size
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"

    # add a PET VEREOS
    sim.add_material_database(paths.gate_data / "GateMaterials_pet.db")
    pet = pet_vereos.add_pet(sim, "pet", create_housing=True, create_mat=False)

    # add table
    bed = pet_vereos.add_table(sim, "pet")

    # add NECR phantom
    phantom = phantom_necr.add_necr_phantom(sim, "phantom")

    # physics
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option4"
    sim.set_cut("world", "all", 1 * m)
    sim.set_cut(phantom.name, "all", 10 * mm)
    sim.set_cut(bed.name, "all", 10 * mm)
    sim.set_cut(f"{pet.name}_crystal", "all", 0.1 * mm)

    # default source for tests
    source = phantom_necr.add_necr_source(sim, phantom)
    total_yield = gate.get_rad_yield("F18")
    print("Yield for F18 (nb of e+ per decay) : ", total_yield)
    source.activity = 3000 * Bq * total_yield
    source.activity = 1787.914158 * MBq * total_yield
    source.half_life = 6586.26 * sec
    source.energy.type = "F18_analytic"  # WARNING not ok, but similar to previous Gate
    # source.energy.type = "F18"  # this is the correct F18 e+ source

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    l = sim.get_all_volumes_user_info()
    crystal = l[[k for k in l if "crystal" in k][0]]
    return crystal


def add_digitizer(sim, paths, nb, crystal):
    # hits collection
    hc = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hc.mother = crystal.name
    print("Crystal :", crystal.name)
    hc.output = paths.output / f"test037_test{nb}.root"
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
    sc.output = hc.output

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
    gate.warning(f"Check root (hits)")
    k1, k2 = default_root_hits_branches()
    p1 = gate.root_compare_param_tree(ref_hits_output, "Hits", k1)
    # in the legacy gate, some edep=0 are still saved in the root file,
    # so we don't count that ones in the histogram comparison
    p1.mins[k1.index("edep")] = 0
    p2 = gate.root_compare_param_tree(hits_output, "Hits", k2)
    p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p = gate.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 6  # % tolerance (including the edep zeros)
    p.tols[k1.index("posX")] = 6
    p.tols[k1.index("posY")] = 6
    p.tols[k1.index("posZ")] = 1.5
    p.tols[k1.index("edep")] = 0.002
    p.tols[k1.index("time")] = 0.0001
    is_ok = gate.root_compare4(p1, p2, p)

    return is_ok


def check_root_singles(
    paths, v, ref_singles_output, singles_output, sname="Singles", png_output="auto"
):
    if png_output == "auto":
        png_output = f"test037_test{v}_singles.png"
    # check phsp (singles)
    print()
    gate.warning(f"Check root (singles)")
    k1, k2 = default_root_singles_branches()
    p1 = gate.root_compare_param_tree(ref_singles_output, "Singles", k1)
    # in the legacy gate, some edep=0 are still saved in the root file,
    # so we don't count that ones in the histogram comparison
    p1.mins[k1.index("energy")] = 0
    p2 = gate.root_compare_param_tree(singles_output, sname, k2)
    p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p = gate.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 5  # % tolerance (including the edep zeros)
    p.tols[k1.index("globalPosX")] = 5
    p.tols[k1.index("globalPosY")] = 5
    p.tols[k1.index("globalPosZ")] = 1.5
    p.tols[k1.index("energy")] = 0.003
    p.tols[k1.index("time")] = 0.0001

    is_ok = gate.root_compare4(p1, p2, p)

    return is_ok
