#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
import os
import subprocess

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test032")

    is_ok = True

    # test 1 = 10mm and with shell
    f1 = paths.output / "iec_10mm.mhd"
    f2 = paths.output / "iec_source_10mm.mhd"
    path_voxelize_script = os.path.join(
        os.path.dirname(__file__), "..", "..", "bin", "voxelize_iec_phantom.py"
    )
    cmd = (
        f"python {path_voxelize_script} -o {f1} "
        f"-s 10 "
        f"--output_source {f2} "
        f"-a 666 555 444 333 222 111 "
    )
    print(cmd)
    # r = os.system(f"{cmd}")
    subprocess.call(cmd.split())

    # if r != 0:
    #    is_ok = False

    # test 2 = 9mm and without shell
    f3 = paths.output / "iec_9mm.mhd"
    f4 = paths.output / "iec_source_9mm.mhd"
    cmd = (
        f"python {path_voxelize_script} -o {f3} "
        f"-s 9 "
        f"--output_source {f4} "
        f"-a 111 222 333 444 555 666 "
        f"--no_shell "
    )
    print(cmd)
    # r = os.system(f"{cmd}")
    subprocess.call(cmd.split())
    # if r != 0:
    #    is_ok = False

    # compare images
    gate.exception.warning("\nDifference with ref image")
    is_ok = (
        utility.assert_images(
            paths.output_ref / "iec_10mm.mhd", f1, stats=None, tolerance=0.001
        )
        and is_ok
    )
    is_ok = (
        utility.assert_images(
            paths.output_ref / "iec_source_10mm.mhd", f2, stats=None, tolerance=0.001
        )
        and is_ok
    )
    is_ok = (
        utility.assert_images(
            paths.output_ref / "iec_9mm.mhd", f3, stats=None, tolerance=0.001
        )
        and is_ok
    )
    is_ok = (
        utility.assert_images(
            paths.output_ref / "iec_source_9mm.mhd", f4, stats=None, tolerance=0.001
        )
        and is_ok
    )
    utility.test_ok(is_ok)
