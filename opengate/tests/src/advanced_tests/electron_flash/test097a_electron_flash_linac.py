from test097_electron_flash_linac_helper import *

import opengate as gate
from opengate.tests import utility

# test_ElectronFlash_dose_app40.py


if __name__ == "__main__":
    # =====================================================
    # INITIALISATION
    # =====================================================

    paths = utility.get_default_test_paths(
        __file__, output_folder="test097_electron_flash_linac"
    )

    sim = create_electron_flash_simulation(
        paths, passive_collimation="app40", fantom="WaterBox"
    )

    sim.run()

    # =====================================================
    # Perform test
    # =====================================================

    path_reference_dose = paths.output_ref / "dose_reference_app40_dose.mhd"
    path_test_dose = sim.get_actor("dose").dose.get_output_path()
    is_ok, mae = analyze_dose(path_reference_dose, path_test_dose)
    tolerance = 0.15
    is_ok, mae = analyze_dose(path_reference_dose, path_test_dose, tolerance)
    utility.test_ok(
        is_ok,
        f"Analyze dose between\n"
        f"path_reference_dose {path_reference_dose} \n"
        f"path_test_dose {path_test_dose} \n"
        f"Mae: {mae:.2f} | (tolerance is {tolerance:.2f} ) \n\n"
        f" ",
    )
