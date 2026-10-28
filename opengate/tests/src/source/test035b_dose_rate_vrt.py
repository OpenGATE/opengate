#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import json
import sys
import numpy as np
import itk
from box import Box
import opengate as gate
from opengate.contrib.dose.doserate import create_simulation, merge_vrt_dose_rate
from opengate.tests import utility


def run_simulation(vrt_mode="analog", activity=5e5, threads=None, skip=False):
    if threads is None:
        threads = 1 if sys.platform.startswith("win") else 4
    folder_name = "test035b_" + vrt_mode
    paths = utility.get_default_test_paths(__file__, "", output_folder=folder_name)
    dr_data = paths.data / "dose_rate_data"

    # Set parameters
    param = Box()
    param.ct_image = str(dr_data / "29_CT_5mm_crop.mhd")
    param.table_mat = str(dr_data / "Schneider2000MaterialsTable.txt")
    param.table_density = str(dr_data / "Schneider2000DensitiesTable.txt")
    param.activity_image = str(dr_data / "activity_test_crop_4mm.mhd")
    param.radionuclide = "Lu177"
    param.activity_bq = activity
    param.number_of_threads = threads
    param.visu = False
    param.verbose = True
    param.density_tolerance_gcm3 = 0.05
    param.output_folder = str(paths.output)
    param.mode = "" if vrt_mode == "analog" else vrt_mode

    # Create the simulation
    sim = create_simulation(param)

    # Stats actor
    stats = sim.get_actor("Stats")
    stats.output_filename = f"stats035b_{vrt_mode}.txt"

    # Run in a new process
    if not skip:
        sim.run(start_new_process=True)

    return paths


if __name__ == "__main__":
    activity = 5e5
    e_factor = 1

    # 1. Analog simulation
    print("Analog simulation  ...")
    paths_analog = run_simulation(vrt_mode="analog", activity=activity, skip=False)
    analog_edep = paths_analog.output / "output_edep.mhd"
    analog_unc = paths_analog.output / "output_dose_uncertainty.mhd"

    # 2. VRT simulations using the new API (e- and gamma_tle)
    print()
    print("VRT simulations (e-, low stats) ..")
    paths_vrt_e = run_simulation(
        vrt_mode="e-", activity=int(activity / e_factor), skip=False
    )

    print()
    print("VRT simulations (gamma tle) ..")
    paths_vrt_gamma = run_simulation(vrt_mode="gamma_tle", activity=activity)

    # 3. Merge outputs using merge_vrt_dose_rate
    paths_vrt_merged = utility.get_default_test_paths(
        __file__, "", output_folder="test035b_vrt"
    )
    print(
        f"\nMerging VRT outputs into {paths_vrt_merged.output} (e_factor={e_factor})..."
    )
    merged_files = merge_vrt_dose_rate(
        paths_vrt_e.output,
        paths_vrt_gamma.output,
        paths_vrt_merged.output,
        e_factor=e_factor,
    )
    print(f"Merged {len(merged_files)} files: {[str(f) for f in merged_files]}")

    vrt_edep = paths_vrt_merged.output / "output_edep.mhd"
    vrt_dose = paths_vrt_merged.output / "output_dose.mhd"
    vrt_unc = paths_vrt_merged.output / "output_dose_uncertainty.mhd"

    # 4. Check dose (edep)
    print()
    gate.exception.warning("Check dose (edep)")
    is_ok = utility.assert_images(
        analog_edep,
        vrt_edep,
        tolerance=30,
        ignore_value_data2=0,
    )

    # 5. Check uncertainty & efficiency
    print()
    gate.exception.warning("Check dose uncertainty & efficiency")
    if vrt_unc.exists():
        img_unc_vrt = itk.imread(str(vrt_unc))
        arr_unc_vrt = itk.GetArrayFromImage(img_unc_vrt)
        arr_dose_vrt = itk.GetArrayFromImage(itk.imread(str(vrt_dose)))
        mask_vrt = arr_dose_vrt > 0

        mean_unc_vrt = (
            float(np.mean(arr_unc_vrt[mask_vrt])) if np.any(mask_vrt) else 0.0
        )
        var_vrt = (
            float(np.mean(arr_unc_vrt[mask_vrt] ** 2)) if np.any(mask_vrt) else 0.0
        )
        unc_valid = (0.0 < mean_unc_vrt < 1.0) and not np.isnan(mean_unc_vrt)
        utility.print_test(
            unc_valid, f"VRT dose uncertainty is valid (mean = {mean_unc_vrt:.4f})"
        )
        is_ok = is_ok and unc_valid

        if analog_unc.exists():
            img_unc_analog = itk.imread(str(analog_unc))
            arr_unc_analog = itk.GetArrayFromImage(img_unc_analog)
            arr_dose_analog = itk.GetArrayFromImage(itk.imread(str(analog_edep)))
            mask_analog = arr_dose_analog > 0

            mean_unc_analog = (
                float(np.mean(arr_unc_analog[mask_analog]))
                if np.any(mask_analog)
                else 0.0
            )
            var_analog = (
                float(np.mean(arr_unc_analog[mask_analog] ** 2))
                if np.any(mask_analog)
                else 0.0
            )

            print(f"Analog dose uncertainty: mean = {mean_unc_analog:.4f}")
            print(f"VRT    dose uncertainty: mean = {mean_unc_vrt:.4f}")

            # Variance reduction check: VRT uncertainty should be lower than analog
            is_reduced = mean_unc_vrt < mean_unc_analog
            utility.print_test(
                is_reduced,
                f"VRT uncertainty is lower than analog ({mean_unc_vrt:.4f} < {mean_unc_analog:.4f})",
            )
            is_ok = is_ok and is_reduced

            # Compute efficiency & speedup
            try:
                stats_a = paths_analog.output / "stats035b_analog.txt"
                stats_e = paths_vrt_e.output / "stats035b_e-.txt"
                stats_g = paths_vrt_gamma.output / "stats035b_gamma_tle.txt"
                if stats_a.exists() and stats_e.exists() and stats_g.exists():
                    with open(stats_a) as f:
                        t_analog = json.load(f)["duration"]["value"]
                    with open(stats_e) as f:
                        t_e = json.load(f)["duration"]["value"]
                    with open(stats_g) as f:
                        t_g = json.load(f)["duration"]["value"]
                    t_vrt = t_e + t_g

                    eff_analog = 1.0 / (t_analog**2 * var_analog)
                    eff_vrt = 1.0 / (t_vrt**2 * var_vrt)
                    speedup = eff_vrt / eff_analog

                    print(
                        f"\nTime: Analog = {t_analog:.2f} s, VRT = {t_vrt:.2f} s (e-: {t_e:.2f} s, gamma: {t_g:.2f} s)"
                    )
                    print(
                        f"Efficiency 1 / (t^2 * var): Analog = {eff_analog:.4e}, VRT = {eff_vrt:.4e}"
                    )
                    print(f"Estimated speedup: {speedup:.2f}x")
            except Exception as e:
                print(f"Could not compute speedup: {e}")

    utility.test_ok(is_ok)
