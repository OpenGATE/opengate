#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import opengate as gate
import test049_pet_digit_blurring_helpers as t49
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test049_pet_blur", "test049")

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
    t49.create_simulation(sim, singles_name="Singles_readout")

    # const
    ns = gate.g4_units.ns
    keV = gate.g4_units.keV
    sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))
    fwhm_to_sigma = 1.0 / sigma_to_fwhm

    # add (fake) blur
    ro = sim.get_actor("Singles_readout")
    bc1 = sim.add_actor("DigitizerBlurringActor", "Singles_1")
    bc1.output_filename = ro.output_filename
    bc1.input_digi_collection = "Singles_readout"
    bc1.blur_attribute = "GlobalTime"
    bc1.blur_method = "Gaussian"
    bc1.blur_fwhm = 100 * ns

    bc2 = sim.add_actor("DigitizerBlurringActor", "Singles")
    bc2.output_filename = ro.output_filename
    bc2.input_digi_collection = bc1.name
    bc2.blur_attribute = "TotalEnergyDeposit"
    bc2.blur_method = "InverseSquare"
    bc2.blur_resolution = 0.18
    bc2.blur_reference_value = 511 * keV

    # start simulation
    sim.run()

    # print results
    stats = sim.get_actor("Stats")
    print(stats)

    # ----------------------------------------------------------------------------------------------------------
    readout = sim.get_actor("Singles_readout")
    ig = readout.GetIgnoredHitsCount()
    print()
    print(f"Nb of ignored hits : {ig}")

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    p = paths.gate_output
    stats_ref = utility.read_stat_file(p / "stats_blur.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.025)

    # check root singles
    f = p / "pet_blur.root"
    bc = sim.get_actor("Singles")
    is_ok = (
        t49.check_root_singles(
            paths, 1, f, bc.get_output_path(), png_output="test049_singles_wb.png"
        )
        and is_ok
    )

    # timing
    b = t49.check_timing(f, bc.get_output_path())
    is_ok = is_ok and b

    utility.test_ok(is_ok)
