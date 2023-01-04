#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test049_pet_digit_blurring_helpers import *
import numpy as np

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
create_simulation(sim, singles_name="Singles_readout")

# const
ns = gate.g4_units("ns")
keV = gate.g4_units("keV")
sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))
fwhm_to_sigma = 1.0 / sigma_to_fwhm

# add (fake) blur
ro = sim.get_actor_user_info("Singles_readout")
bc1 = sim.add_actor("DigitizerBlurringActor", "Singles_1")
bc1.output = ro.output
bc1.input_digi_collection = "Singles_readout"
bc1.blur_attribute = "GlobalTime"
bc1.blur_method = "Gaussian"
bc1.blur_fwhm = 100 * ns

bc2 = sim.add_actor("DigitizerBlurringActor", "Singles")
bc2.output = ro.output
bc2.input_digi_collection = bc1.name
bc2.blur_attribute = "TotalEnergyDeposit"
bc2.blur_method = "InverseSquare"
bc2.blur_resolution = 0.18
bc2.blur_reference_value = 511 * keV

# start simulation
output = sim.start()

# print results
stats = output.get_actor("Stats")
print(stats)

# ----------------------------------------------------------------------------------------------------------
readout = output.get_actor("Singles_readout")
ig = readout.GetIgnoredHitsCount()
print()
print(f"Nb of ignored hits : {ig}")

# check stats
print()
gate.warning(f"Check stats")
p = paths.gate_output
stats_ref = gate.read_stat_file(p / "stats_blur.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.025)

# check root singles
f = p / "pet_blur.root"
bc = output.get_actor("Singles").user_info
is_ok = (
    check_root_singles(paths, 1, f, bc.output, png_output="test049_singles_wb.png")
    and is_ok
)

# timing
b = check_timing(f, bc.output)
is_ok = is_ok and b

gate.test_ok(is_ok)
