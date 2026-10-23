#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
When torch is installed, itk imports it at the first use of an image function
(about 1 s). opengate makes itk import torch only when it is needed
(opengate/itk_torch.py). Check, each case in a new Python process:
- opengate and itk images used without torch: torch is not imported;
- torch imported after opengate: itk functions still accept torch tensors;
- torch imported before opengate: same.
"""

import importlib.util
import subprocess
import sys

from opengate.tests import utility

common = """
import sys
import numpy as np
import itk
import opengate as gate
from opengate.image import create_3d_image
img = create_3d_image([8, 8, 8], [1, 1, 1], pixel_type="float")
itk.median_image_filter(img, radius=1)
itk.median_image_filter(np.zeros((8, 8, 8), dtype=np.float32), radius=1)
"""

without_torch = common + """
print("TORCH_IMPORTED" if "torch" in sys.modules else "TORCH_NOT_IMPORTED")
"""

torch_after = common + """
import torch
t = torch.rand(1, 8, 8)
out = itk.median_image_filter(t, radius=1)
ref = itk.median_image_filter(t.numpy(), radius=1)
assert isinstance(out, torch.Tensor), type(out)
assert np.allclose(out.numpy().squeeze(), np.asarray(ref).squeeze())
print("TENSOR_OK")
"""

torch_before = "import torch\n" + torch_after


def run(name, code, expected):
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=600
    )
    b = r.returncode == 0 and expected in r.stdout
    utility.print_test(b, f"{name}: {expected if b else 'FAILED'}")
    if not b:
        print(r.stdout[-2000:], r.stderr[-2000:])
    return b


if __name__ == "__main__":
    is_ok = True
    if importlib.util.find_spec("torch") is None:
        # without torch, itk never imports it: only check that itk works
        is_ok = run("itk without torch installed", without_torch, "NOT_IMPORTED")
    else:
        is_ok = run("no torch use", without_torch, "TORCH_NOT_IMPORTED") and is_ok
        is_ok = run("torch imported after opengate", torch_after, "TENSOR_OK") and is_ok
        is_ok = (
            run("torch imported before opengate", torch_before, "TENSOR_OK") and is_ok
        )
    utility.test_ok(is_ok)
