from test097_electron_flash_linac_helper import *

import opengate as gate
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, output_folder="test097_electron_flash_linac"
    )

    sim = create_electron_flash_simulation(
        paths, passive_collimation="nose", fantom="Phasespace_plane"
    )

    sim.run()

    # =====================================================
    # Perform test
    # =====================================================

    path_reference_root_phsp = paths.output_ref / "phsp_reference_nose.root"
    path_test_root_phsp = sim.get_actor("PhaseSpace").get_output_path()
    is_ok = analyze_root(paths, path_reference_root_phsp, path_test_root_phsp)

    utility.test_ok(is_ok)
