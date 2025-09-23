#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import test028_ge_nm670_spect_2_helpers as test028
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="test028_proj_blur"
    )

    # create the simulation
    sim = gate.Simulation()

    # main description
    spect = test028.create_spect_simu(sim, paths, 1)
    proj = test028.test_add_proj(sim)

    # change the digitizer to add blurring between the adder and the energy window
    mm = gate.g4_units.mm
    hc = sim.actor_manager.get_actor("Hits")
    sc = sim.actor_manager.get_actor("Singles")
    cc = sim.actor_manager.get_actor("EnergyWindows")

    bc = sim.add_actor("DigitizerSpatialBlurringActor", "Singles_blur")
    bc.output_filename = sc.output_filename
    bc.attached_to = "spect_crystal"  # important !
    bc.input_digi_collection = sc.name
    bc.blur_attribute = "PostPosition"
    bc.use_truncated_Gaussian = False
    # r = 20 * mm
    bc.blur_fwhm = 20 * mm
    bc.keep_in_solid_limits = True

    # input of EnergyWindows is the blur one
    cc.input_digi_collection = "Singles_blur"

    # we modify the priority to have the correct actors order
    hc.priority = 90
    sc.priority = 91
    bc.priority = 92
    cc.priority = 93

    # rotate spect
    cm = gate.g4_units.cm
    test028.nm670.rotate_gantry(spect, 10 * cm, -15)

    sec = gate.g4_units.second
    sim.run_timing_intervals = [[1 * sec, 2 * sec]]

    print(sim)
    sim.run()

    # print stats
    stats = sim.get_actor("Stats")
    print(stats)

    # check singles
    print()
    gate.exception.warning(
        "Compare singles blur vs unblur (it is normal that it dont match)"
    )
    hc_file = sim.get_actor("Singles_blur").get_output_path()
    ref_file = paths.output_ref / hc_file.name
    print(hc_file)
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 3, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 2, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 3, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.1,
            "scaling": 1,
        },
    ]
    is_ok = utility.compare_root2(
        ref_file,
        hc_file,
        "Singles",
        "Singles_blur",
        checked_keys,
        paths.output / f"test028_singles_blur_unblur.png",
    )

    # check singles
    print()
    version = "3_blur"
    gate.exception.warning("Compare singles")
    hc_file = sim.get_actor("Singles_blur").get_output_path()
    ref_file = paths.output_ref / hc_file.name
    print(hc_file)
    checked_keys = [
        {"k1": "PostPosition_X", "k2": "PostPosition_X", "tol": 0.9, "scaling": 1},
        {"k1": "PostPosition_Y", "k2": "PostPosition_Y", "tol": 0.3, "scaling": 1},
        {"k1": "PostPosition_Z", "k2": "PostPosition_Z", "tol": 0.4, "scaling": 1},
        {
            "k1": "TotalEnergyDeposit",
            "k2": "TotalEnergyDeposit",
            "tol": 0.0002,
            "scaling": 1,
        },
    ]
    is_ok = (
        utility.compare_root2(
            ref_file,
            hc_file,
            "Singles_blur",
            "Singles_blur",
            checked_keys,
            paths.output / f"test028_singles.png",
        )
        and is_ok
    )

    # check projection
    proj_out = sim.get_actor("Projection")
    is_ok = test028.test_spect_proj(sim, paths, proj_out) and is_ok

    utility.test_ok(is_ok)
