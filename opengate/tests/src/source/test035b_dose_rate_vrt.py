#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import itk
from box import Box

import opengate as gate
from opengate.contrib.dose.doserate import create_simulation
from opengate.tests import utility


def run_simulation_vrt(vrt_mode=""):
    paths = utility.get_default_test_paths(
        __file__, "", output_folder="test035b_" + vrt_mode
    )
    dr_data = paths.data / "dose_rate_data"

    # set param
    gcm3 = gate.g4_units.g_cm3
    param = Box()
    param.ct_image = str(dr_data / "29_CT_5mm_crop.mhd")
    param.table_mat = str(dr_data / "Schneider2000MaterialsTable.txt")
    param.table_density = str(dr_data / "Schneider2000DensitiesTable.txt")
    param.activity_image = str(dr_data / "activity_test_crop_4mm.mhd")
    param.radionuclide = "Lu177"
    param.activity_bq = 5e5
    param.number_of_threads = 1
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = str(paths.output)
    param.mode = vrt_mode

    # Create the simu
    # Note that the returned sim object can be modified to change source or cuts or whatever other parameters
    sim = create_simulation(param)

    # stats
    stats = sim.get_actor("Stats")
    stats.output_filename = "stats035_" + vrt_mode + ".txt"

    print("Phys list cuts:")
    print(sim.physics_manager.dump_production_cuts())

    # run
    if not vrt_mode == "":
        sim.run(start_new_process=True)
    return paths


if __name__ == "__main__":
    paths_original_simu = run_simulation_vrt(
        vrt_mode=""
    )  # too long do not run the simulation without vrt, use reference output
    paths_vrt_e_simu = run_simulation_vrt(vrt_mode="e-")
    paths_vrt_gamma_simu = run_simulation_vrt(vrt_mode="gamma")

    # dose comparison between original simu and vrt simu (electron + gamma)
    print()
    gate.exception.warning(f"Check dose")
    dose_vrt_e_simu = itk.imread(paths_vrt_e_simu.output / "edep_edep.mhd")
    dose_vrt_gamma_simu = itk.imread(paths_vrt_gamma_simu.output / "edep_edep.mhd")
    array_vrt_e_simu = itk.GetArrayFromImage(dose_vrt_e_simu)
    array_vrt_gamma_simu = itk.GetArrayFromImage(dose_vrt_gamma_simu)
    array_vrt = array_vrt_e_simu + array_vrt_gamma_simu
    dose_vrt = itk.GetImageFromArray(array_vrt)
    dose_vrt.CopyInformation(dose_vrt_e_simu)
    itk.imwrite(dose_vrt, paths_original_simu.output / "edep_edep_vrt.mhd")
    is_ok = utility.assert_images(
        paths_original_simu.output_ref / "edep_edep.mhd",
        paths_original_simu.output / "edep_edep_vrt.mhd",
        tolerance=30,
        ignore_value_data2=0,
    )
    utility.test_ok(is_ok)
