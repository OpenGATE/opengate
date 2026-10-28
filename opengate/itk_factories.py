"""
Make the first itk image read/write fast when itk-rtk is installed.

At the first image read or write, itk registers all its image file formats
(ImageIO factories): it loads every itk module that provides one. RTK
(itk-rtk, installed by some SPECT tools) provides 8 formats (His, Hnd, XRad,
...) and depends on many itk modules, so this first read or write takes about
15 s more when itk-rtk is installed, in every process, although opengate never
uses these formats.

So the RTK formats are not registered at the first read or write any more:
they are registered when the RTK module is loaded, i.e. when RTK is used (e.g.
`from itk import RTK`). Only reading or writing an RTK file format without
using RTK first is not possible any more.
"""

import functools
import sys

# itk modules with ImageIO factories that are only registered when the module
# is loaded
_DEFERRED_MODULES = ("RTK",)


def defer_itk_io_factories_of_unused_modules():
    try:
        import itk.support.base as base
    except Exception:
        return
    modules = getattr(base, "itk_base_global_module_data", None)
    load = getattr(base, "itk_load_swig_module", None)
    if (
        modules is None
        or load is None
        or not hasattr(base, "_factories_loaded")
        or getattr(load, "_opengate_deferred_factories", False)
    ):
        # another itk version, or already done
        return

    deferred = {}
    for name in _DEFERRED_MODULES:
        data = modules.get(name)
        if data is None or not getattr(data, "_factories", None):
            continue
        if hasattr(sys.modules.get(f"itk.{name}Python"), "__templates_loaded"):
            # already loaded: its factories are registered
            continue
        deferred[name] = data._factories
        data._factories = ()
    if not deferred:
        return

    @functools.wraps(load)
    def itk_load_swig_module(name, namespace=None):
        load(name, namespace)
        factories = deferred.pop(name, None)
        if factories is None:
            return
        # the module is now loaded: its factories are restored, and registered
        # for the kinds (e.g. ImageIO) that itk has already registered
        modules[name]._factories = factories
        ns = {}
        load(name, ns)
        for kind, prefix in factories:
            if kind in base._factories_loaded:
                ns[f"{prefix}{kind}Factory"].RegisterOneFactory()

    itk_load_swig_module._opengate_deferred_factories = True
    base.itk_load_swig_module = itk_load_swig_module
