#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from test097_electron_flash_linac_helper import *

import opengate as gate
from opengate.tests import utility

# test MB slit

if __name__ == "__main__":
    # =====================================================
    # INITIALISATION
    # =====================================================
    paths = utility.get_default_test_paths(
        __file__, output_folder="test097_electron_flash_linac"
    )

    sim = create_electron_flash_simulation(
        paths, passive_collimation="mb_40_slit_11", fantom="WaterBox"
    )

    sim.run()

    # =====================================================
    # Perform test
    # =====================================================

    path_reference_dose = paths.output_ref / "dose_reference_mb_40_slit_11_dose.mhd"
    path_test_dose = sim.get_actor("dose").dose.get_output_path()
    # The dose voxels are 0.1 mm here (1 mm for the other test097 dose tests):
    # the PDD is computed in a central square of 100 voxels = 10 mm (about
    # the beam width). With the default 10 voxels (1 mm), almost no dose is
    # deposited in the square with 5000 primaries: the MAE was random (0.37 -
    # 0.58 for 5 seeds), the test failed at random with a 0.55 tolerance.
    # With 10 mm: MAE 0.11 - 0.22 for 5 seeds.
    tolerance = 0.3
    is_ok, mae = analyze_dose(
        path_reference_dose, path_test_dose, tolerance, mean_size=100
    )
    utility.test_ok(
        is_ok,
        f"Analyze dose between\n"
        f"path_reference_dose {path_reference_dose} \n"
        f"path_test_dose {path_test_dose} \n"
        f"Mae: {mae:.2f} | (tolerance is {tolerance:.2f} ) \n\n"
        f" ",
    )
