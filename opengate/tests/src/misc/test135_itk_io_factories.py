#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 135: the RTK image formats are only registered when RTK is used
(opengate/itk_factories.py).

In a new Python process:
1. import opengate, write and read an image: RTK is not loaded
2. use RTK: the RTK image formats (e.g. His) are registered

Skipped if itk-rtk is not installed.
"""

import subprocess
import sys

from opengate.tests import utility

child_code = """
import sys
import numpy as np
import opengate
import itk

def rtk_loaded():
    return hasattr(sys.modules.get("itk.RTKPython"), "__templates_loaded")

def factories():
    return [str(f.GetDescription()) for f in itk.ObjectFactoryBase.GetRegisteredFactories()]

img = itk.image_from_array(np.zeros((4, 4, 4), dtype=np.float32))
itk.imwrite(img, sys.argv[1])
img2 = itk.imread(sys.argv[1])
ok = np.allclose(itk.array_view_from_image(img2), 0)
print("RESULT_IO", ok and not rtk_loaded(), rtk_loaded())

from itk import RTK
_ = RTK.ConstantImageSource
his = any(f.startswith("His ImageIO") for f in factories())
print("RESULT_RTK", rtk_loaded() and his, rtk_loaded(), his)
"""


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test135")
    try:
        import itk.support.base as base

        has_rtk = "RTK" in base.itk_base_global_module_data
    except Exception:
        has_rtk = False
    if not has_rtk:
        print("itk-rtk is not installed: test skipped")
        utility.test_ok(True)
        sys.exit(0)

    paths.output.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, "-c", child_code, str(paths.output / "image.mhd")],
        capture_output=True,
        text=True,
    )
    out = r.stdout + r.stderr
    print(out[-2000:])

    is_ok = utility.print_test(
        "RESULT_IO True" in out,
        "Image written and read, RTK not loaded",
    )
    is_ok = (
        utility.print_test(
            "RESULT_RTK True" in out,
            "RTK used: its image formats are registered",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
