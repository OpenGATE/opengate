#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy as np
import opengate.contrib.pet.siemensbiograph as pet_biograph
import opengate as gate
import opengate.contrib.phantoms.necr as phantom_necr
from test037_pet_hits_singles_helpers import (
    default_root_hits_branches,
    default_root_singles_branches,
)
from opengate.userhooks import check_production_cuts
from opengate.tests import utility

paths = utility.get_default_test_paths(__file__, "gate_test049_pet_blur", "test049")


def create_simulation(sim, threads=1, singles_name="Singles"):
    # main options
    sim.visu = False
    sim.number_of_threads = threads
    sim.random_seed = 123456789

    # units
    m = gate.g4_units.m
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    MBq = Bq * 1e6
    sec = gate.g4_units.second

    #  change world size and material
    sim.world.size = [2 * m, 2 * m, 2 * m]
    sim.world.material = "G4_AIR"

    # add a PET Biograph
    pet = pet_biograph.add_pet(sim, "pet")
    singles = pet_biograph.add_digitizer(
        sim, pet.name, paths.output / f"test049_pet.root", singles_name=singles_name
    )

    # add NECR phantom
    phantom = phantom_necr.add_necr_phantom(sim, "phantom")

    # physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.global_production_cuts.all = 1 * m
    sim.physics_manager.set_production_cut(phantom.name, "all", 10 * mm)
    sim.physics_manager.set_production_cut(f"{pet.name}_crystal", "all", 0.1 * mm)

    # default source for tests
    source = phantom_necr.add_necr_source(sim, phantom)
    total_yield = gate.sources.generic.get_rad_yield("F18")
    print("Yield for F18 (nb of e+ per decay) : ", total_yield)
    source.activity = 3000 * Bq * total_yield
    source.activity = 1787.914158 * MBq * total_yield / sim.number_of_threads
    # source.n = 50000
    source.half_life = 6586.26 * sec
    source.energy.type = "F18_analytic"  # WARNING not ok, but similar to previous Gate
    # source.energy.type = "F18"  # this is the correct F18 e+ source

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # timing
    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.00005 * sec]]
    # sim.run_timing_intervals = [[0, 0.00005 * sec]]

    # set user hook to dump production cuts from G4
    sim.user_hook_after_init = check_production_cuts


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
    # p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p1.scaling[p1.the_keys.index("time")] = 1e9  # time in ns
    p = utility.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 6  # % tolerance (including the edep zeros)
    p.tols[k1.index("posX")] = 12
    p.tols[k1.index("posY")] = 13
    p.tols[k1.index("posZ")] = 2.1
    p.tols[k1.index("edep")] = 0.003
    p.tols[k1.index("time")] = 480
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
    # p2.scaling[p2.the_keys.index("GlobalTime")] = 1e-9  # time in ns
    p1.scaling[p1.the_keys.index("time")] = 1e9  # time in ns
    p = utility.root_compare_param(p1.the_keys, paths.output / png_output)
    p.hits_tol = 5  # % tolerance (including the edep zeros)
    p.tols[k1.index("globalPosX")] = 8
    p.tols[k1.index("globalPosY")] = 5
    p.tols[k1.index("globalPosZ")] = 1.2
    p.tols[k1.index("energy")] = 0.0045
    p.tols[k1.index("time")] = 351

    is_ok = utility.root_compare4(p1, p2, p)

    return is_ok


def check_timing(
    ref_root_file,
    root_file,
):
    times_ref = uproot.open(ref_root_file)["Hits"].arrays(library="numpy")["time"] * 1e9
    times = uproot.open(root_file)["Hits"].arrays(library="numpy")["GlobalTime"]

    def rel_d(a, b, norm, tol):
        r = np.fabs(a - b) / norm * 100
        s = f"{a:.2f}(ref) {b:.2f}(this) {r:.2f}% (rel. diff.), tolerance: {tol:.2f}%"
        is_ok = r < tol
        return s, is_ok

    def compare_stat(ref, val, tol):
        m = np.mean(ref)
        s1, is_ok1 = rel_d(np.min(ref), np.min(val), m, tol)
        s2, is_ok2 = rel_d(m, np.mean(val), m, tol)
        s3, is_ok3 = rel_d(np.max(ref), np.max(val), m, tol)
        s = f"Min: {s1}    Mean: {s2}     Max: {s3}"
        return s, is_ok1 and is_ok2 and is_ok3

    tol = 1.2
    s, b = compare_stat(times_ref, times, tol)
    print()
    utility.print_test(b, f"Hits timing ref:\n{s}, Passed? {b}")
    is_ok = b

    times_ref = (
        uproot.open(ref_root_file)["Singles"].arrays(library="numpy")["time"] * 1e9
    )
    times = uproot.open(root_file)["Singles"].arrays(library="numpy")["GlobalTime"]

    print()
    s, b = compare_stat(times_ref, times, tol)
    utility.print_test(b, f"Singles timing ref:\n {s}, Passed? {b}")
    is_ok = is_ok and b

    print()
    min_ref = np.min(times_ref)
    min_v = np.min(times)
    tol = -10
    b = min_v < tol
    utility.print_test(
        b,
        f"Compare time min values: Ref: {min_ref} vs this: {min_v}, "
        f"Must be smaller than {tol}, Passed? {b}",
    )

    return is_ok and b
