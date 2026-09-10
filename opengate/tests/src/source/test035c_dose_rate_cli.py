#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pathlib
import tempfile
from click.testing import CliRunner

from opengate.bin.dose_rate import go
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test035c")
    dr_data = paths.data / "dose_rate_data"

    is_ok = True
    runner = CliRunner()

    print("=== Test 1: CLI help and argument checking ===")
    res_help = runner.invoke(go, ["--help"])
    print(f"  --help exit code: {res_help.exit_code}")
    if res_help.exit_code != 0 or "--mode" not in res_help.output:
        is_ok = False

    res_missing = runner.invoke(go, [])
    print(f"  Missing json exit code: {res_missing.exit_code}")
    if res_missing.exit_code == 0:
        is_ok = False

    res_notfound = runner.invoke(go, ["non_existent_file.json"])
    print(f"  Non-existent json exit code: {res_notfound.exit_code}")
    if res_notfound.exit_code == 0:
        is_ok = False

    print("\n=== Test 2: Incompatible mode and radionuclide validation ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        dummy_json = tmp / "dummy.json"
        dummy_json.write_text(
            json.dumps({"ct_image": "dummy.mhd", "radionuclide": "89 225"})
        )

        # Radionuclide '89 225' (Ac225) with --mode vrt must fail with informative error
        res_vrt_fail = runner.invoke(go, [str(dummy_json), "--mode", "vrt"])
        print(f"  VRT with ion '89 225' exit code: {res_vrt_fail.exit_code}")
        if (
            res_vrt_fail.exit_code == 0
            or "Error: VRT mode is designed" not in res_vrt_fail.output
        ):
            is_ok = False
        else:
            print("  Rejection message verified successfully.")

    print("\n=== Test 3: --merge-only mode ===")
    dir_e = paths.output_ref.parent / "test035b" / "test035b_e-"
    if not dir_e.exists():
        dir_e = paths.output.parent / "test035b_e-"
    dir_gamma = paths.output_ref.parent / "test035b" / "test035b_gamma_tle"
    if not dir_gamma.exists():
        dir_gamma = paths.output.parent / "test035b_gamma_tle"

    if dir_e.exists() and dir_gamma.exists():
        with tempfile.TemporaryDirectory() as tmpdir:
            out_merge = pathlib.Path(tmpdir) / "merged"
            res_merge = runner.invoke(
                go,
                [
                    "--merge-only",
                    str(dir_e),
                    str(dir_gamma),
                    "-o",
                    str(out_merge),
                    "--e-factor",
                    "1.0",
                ],
            )
            print(f"  --merge-only exit code: {res_merge.exit_code}")
            merged_dose = out_merge / "output_dose.mhd"
            merged_unc = out_merge / "output_dose_uncertainty.mhd"
            if (
                res_merge.exit_code != 0
                or not merged_dose.exists()
                or not merged_unc.exists()
            ):
                print(f"  Merge failed or output missing: {res_merge.output}")
                is_ok = False
            else:
                print("  Merge completed successfully, output images created.")
    else:
        print(f"  Skipping --merge-only (test035b dirs not found: {dir_e})")

    print("\n=== Test 4: Short end-to-end analog CLI run with generic ion ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        cfg = {
            "ct_image": str(dr_data / "29_CT_5mm_crop.mhd"),
            "table_mat": str(dr_data / "Schneider2000MaterialsTable.txt"),
            "table_density": str(dr_data / "Schneider2000DensitiesTable.txt"),
            "activity_image": str(dr_data / "activity_test_crop_4mm.mhd"),
            "density_tolerance_gcm3": 0.2,
            "verbose": False,
        }
        cfg_path = tmp / "param.json"
        cfg_path.write_text(json.dumps(cfg))
        out_sim = tmp / "output_cli"

        # Run with '89 225' (Ac225), low activity (10 Bq), 1 thread
        res_sim = runner.invoke(
            go,
            [
                str(cfg_path),
                "-r",
                "89 225",
                "-a",
                "10",
                "-t",
                "1",
                "-o",
                str(out_sim),
            ],
        )
        print(f"  CLI simulation exit code: {res_sim.exit_code}")
        out_dose = out_sim / "output_dose.mhd"
        out_stats = out_sim / "stats.txt"
        if res_sim.exit_code != 0 or not out_dose.exists() or not out_stats.exists():
            print(f"  Simulation failed or files missing! Output:\n{res_sim.output}")
            is_ok = False
        else:
            print(f"  Simulation produced: {[f.name for f in out_sim.glob('*.mhd')]}")

    utility.test_ok(is_ok)
