#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from box import Box
from opengate.contrib.dose.doserate import create_simulation
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test035")
    dr_data = paths.data / "dose_rate_data"

    # set param
    gcm3 = gate.g4_units.g_cm3
    param = Box()
    param.ct_image = str(dr_data / "29_CT_5mm_crop.mhd")
    param.table_mat = str(dr_data / "Schneider2000MaterialsTable.txt")
    param.table_density = str(dr_data / "Schneider2000DensitiesTable.txt")
    param.activity_image = str(dr_data / "activity_test_crop_4mm.mhd")
    param.radionuclide = "Lu177"
    param.activity_bq = 1e6
    param.number_of_threads = 1
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = str(paths.output)

    # Create the simu
    # Note that the returned sim object can be modified to change source or cuts or whatever other parameters
    sim = create_simulation(param)

    # stats
    stats = sim.get_actor("Stats")
    stats.output_filename = "stats035.txt"

    # Change source to alpha to get quick high local dose
    source = sim.get_source_user_info("vox")
    source.particle = "alpha"
    MeV = gate.g4_units.MeV
    source.energy.mono = 1 * MeV

    print("Phys list cuts:")
    print(sim.physics_manager.dump_production_cuts())

    # run
    sim.run(start_new_process=True)

    # print results
    print()
    print(stats)
    stats_ref = utility.read_stat_file(paths.output_ref / "stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.10)

    # dose comparison
    print()
    gate.exception.warning(f"Check dose")
    h = sim.get_actor("dose")
    print(h)
    is_ok = (
        utility.assert_images(
            paths.output_ref / "edep.mhd",
            h.edep.get_output_path(),
            stats,
            tolerance=15,
            ignore_value=0,
        )
        and is_ok
    )

    utility.test_ok(is_ok)
