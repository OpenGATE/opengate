#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate.contrib.pet_siemens_biograph as pet_biograph
from test037_pet_hits_singles_helpers import *

paths = gate.get_default_test_paths(__file__, "gate_test049_pet_blur")

"""
see https://github.com/teaghan/PET_MonteCarlo
and https://doi.org/10.1002/mp.16032

PET simulation to test blurring options of the digitizer

- PET:
- phantom: nema necr
- output: singles with and without various blur options

"""

# create the simulation
sim = gate.Simulation()

# main options
sim.user_info.visu = False

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
Bq = gate.g4_units("Bq")
MBq = Bq * 1e6
sec = gate.g4_units("second")

#  change world size
world = sim.world
world.size = [2 * m, 2 * m, 2 * m]
world.material = "G4_AIR"

# add a PET Biograph
pet = pet_biograph.add_pet(sim, "pet")
singles = pet_biograph.add_digitizer(sim, pet.name, paths.output / f"test049_pet.root")

# add NECR phantom
phantom = phantom_necr.add_necr_phantom(sim, "phantom")

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "G4EmStandardPhysics_option4"
sim.set_cut("world", "all", 1 * m)
sim.set_cut(phantom.name, "all", 10 * mm)
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

# timing
sec = gate.g4_units("second")
sim.run_timing_intervals = [[0, 0.0001 * sec]]

# create G4 objects
sim.initialize()

# start simulation
sim.start()

# print results
stats = sim.get_actor("Stats")
print(stats)

# ----------------------------------------------------------------------------------------------------------

readout = sim.get_actor("Singles")
ig = readout.GetIgnoredHitsCount()
print()
print(f"Nb of ignored hits : {ig}")

# check stats
print()
gate.warning(f"Check stats")
p = paths.gate_output
stats_ref = gate.read_stat_file(p / "stats.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.01)

# check root hits
hc = sim.get_actor_user_info("Hits")
f = p / "pet.root"
is_ok = check_root_hits(paths, 1, f, hc.output, "test049_hits.png") and is_ok

# check root singles
sc = sim.get_actor_user_info("Singles")
is_ok = (
    check_root_singles(paths, 1, f, sc.output, png_output="test049_singles.png")
    and is_ok
)

gate.test_ok(is_ok)
