"""
Make itk import torch only when it is needed.

When torch is installed (e.g. for garf), itk imports it the first time an
image function is used, to accept torch tensors as inputs: this costs about
1 s in every process that uses itk, even if torch is never used.

A torch tensor can only exist if torch has already been imported. So the itk
decorator is replaced by one that checks, at each call, whether torch is
imported: if not, the plain itk function is used, and torch is not imported;
if yes (also when torch is imported after opengate), the original itk
torch-aware function is used. The behaviour is the same as itk's.
"""

import functools
import sys


def make_itk_import_torch_only_when_needed():
    try:
        import itk.support.helpers as helpers
    except Exception:
        return
    original = getattr(helpers, "accept_array_like_xarray_torch", None)
    if original is None or not hasattr(helpers, "_HAVE_TORCH"):
        # another itk version: leave it as it is
        return
    if not helpers._HAVE_TORCH or getattr(original, "_opengate_lazy_torch", False):
        # torch is not installed, or already done
        return

    # the itk decorator reads _HAVE_TORCH when it is applied (to import torch)
    # and at each call: it is kept equal to "torch is imported", so it goes
    # from False to True once, when torch is imported (it is never removed)
    def update_have_torch():
        helpers._HAVE_TORCH = "torch" in sys.modules
        return helpers._HAVE_TORCH

    def accept_array_like_xarray_torch(image_filter):
        # the itk wrappers, built at their first call, without or with torch
        wrappers = {}

        @functools.wraps(image_filter)
        def image_filter_wrapper(*args, **kwargs):
            with_torch = update_have_torch()
            if with_torch not in wrappers:
                wrappers[with_torch] = original(image_filter)
            return wrappers[with_torch](*args, **kwargs)

        return image_filter_wrapper

    accept_array_like_xarray_torch._opengate_lazy_torch = True
    update_have_torch()
    helpers.accept_array_like_xarray_torch = accept_array_like_xarray_torch
