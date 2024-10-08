#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from box import Box
import json
import numpy as np
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test046")

    radionuclides = ["Tc99m", "Lu177", "In111", "I131"]
    ref_collimators = ["lehr", "megp", "megp", "hegp"]

    # Test 1
    is_ok = True
    for rad, col in zip(radionuclides, ref_collimators):
        collimator = gate_spect.get_collimator(rad)
        ok = True
        if collimator != col:
            ok = False
        utility.print_test(ok, f"Rad {rad}: the collimator is {col}")
        is_ok = is_ok and ok

    # Test 2
    print()
    sim = gate.Simulation()
    sim.output_dir = paths.output
    digit = Box()
    digit_ns = Box()
    for rad in radionuclides:
        channels = gate.actors.digitizers.get_simplified_digitizer_channels_rad(
            "fake_spect", rad, True
        )
        # cc = gate_spect.add_digitizer_energy_windows(sim, 'fake_crystal', channels)
        digit[rad] = channels
        channels = gate.actors.digitizers.get_simplified_digitizer_channels_rad(
            "fake_spect", rad, False
        )
        # cc = gate_spect.add_digitizer_energy_windows(sim, 'fake_crystal', channels)
        digit_ns[rad] = channels

    print(digit)
    print()
    print(digit_ns)

    # reference
    """outfile = open(paths.output_ref / "t046_digitizer.json", "w")
    json.dump(digit, outfile, indent=4)
    outfile = open(paths.output_ref / "t046_digitizer_ns.json", "w")
    json.dump(digit_ns, outfile, indent=4)"""

    # check
    ref_digit = json.loads(open(paths.output_ref / "t046_digitizer.json").read())
    ref_digit_ns = json.loads(open(paths.output_ref / "t046_digitizer_ns.json").read())
    ok = digit == ref_digit
    utility.print_test(ok, f"Test channels (with scatter): {ok}")
    is_ok = is_ok and ok
    ok = digit_ns == ref_digit_ns
    utility.print_test(ok, f"Test channels (without scatter): {ok}")
    is_ok = is_ok and ok

    # Test 3
    print()
    yields = [0.885, 0.172168, 1.847315, 1.0024600000000004]
    i = 0
    for rad in radionuclides:
        w, e = gate.sources.generic.get_rad_gamma_energy_spectrum(rad)
        tw = np.array(w).sum()
        ok = tw == yields[i]
        utility.print_test(ok, f"Test yield {rad}: {tw} {yields[i]} {ok}")
        is_ok = is_ok and ok
        i += 1

    # end
    utility.test_ok(is_ok)
