#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "gate_test028_ge_nm670_spect")

    # create the simulation
    sim = gate.Simulation()

    # main description
    spect = test028.create_spect_simu(sim, paths, number_of_threads=1)

    # change the digitizer to add blurring between the adder and the energy window
    mm = gate.g4_units.mm
    hc = sim.get_actor_user_info("Hits")
    sc = sim.get_actor_user_info("Singles")
    cc = sim.get_actor_user_info("EnergyWindows")

    bc = sim.add_actor("DigitizerSpatialBlurringActor", "Singles_blur")
    bc.output = sc.output
    bc.mother = "spect_crystal"  # important !
    bc.input_digi_collection = sc.name
    bc.blur_attribute = "PostPosition"
    r = 20 * mm
    bc.blur_fwhm = 20 * mm  #  [r, r, r]
    bc.keep_in_solid_limits = True

    # input of EnergyWindows is the blur one
    cc.input_digi_collection = "Singles_blur"

    # we modify the priority to have the correct actors order
    hc.priority = 90
    sc.priority = 91
    cc.priority = 93
    bc.priority = 92

    proj = test028.test_add_proj(sim, paths)

    # rotate spect
    cm = gate.g4_units.cm
    psd = 6.11 * cm
    p = [0, 0, -(20 * cm + psd)]
    spect.translation, spect.rotation = gate.geometry.utility.get_transform_orbiting(
        p, "y", -15
    )

    sec = gate.g4_units.second
    sim.run_timing_intervals = [[1 * sec, 2 * sec]]

    print(sim.user_info)
    sim.run()

    # print stats
    stats = sim.output.get_actor("Stats")
    print(stats)

    # check singles
    print()
    version = "3_blur"
    gate.exception.warning("Compare singles")
    gate_file = paths.gate_output / f"hits{version}.root"
    hc_file = sim.output.get_actor("Singles_blur").user_info.output
    checked_keys = [
        {"k1": "globalPosX", "k2": "PostPosition_X", "tol": 1.8, "scaling": 1},
        {"k1": "globalPosY", "k2": "PostPosition_Y", "tol": 1.3, "scaling": 1},
        {"k1": "globalPosZ", "k2": "PostPosition_Z", "tol": 0.2, "scaling": 1},
        {"k1": "energy", "k2": "TotalEnergyDeposit", "tol": 0.001, "scaling": 1},
    ]
    is_ok = utility.compare_root2(
        gate_file,
        hc_file,
        "Singles",
        "Singles_blur",
        checked_keys,
        paths.output / f"test028_{version}_singles.png",
    )

    # check projection
    proj = sim.output.get_actor("Projection")
    is_ok = test028.test_spect_proj(sim.output, paths, proj, version="3_blur") and is_ok

    utility.test_ok(is_ok)
