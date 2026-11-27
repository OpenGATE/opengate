#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the backend ladder of the VTK visualisation driver (#1228):

- the order is cuda -> vulkan -> metal -> gpu -> cpu;
- 'auto' takes the first usable rung, and records why the others were skipped;
- an explicit backend never degrades silently: it raises when it is unusable;
- OPENGATE_VISU_BACKEND is honoured, an unknown backend is refused;
- the resolution is cached (the probe must not run per frame).

The probe itself is replaced by a fake, so this test needs no GPU and no vtk.
"""

import os

from opengate import visualization as visu
from opengate.tests import utility

# probe in this process: the probe itself is replaced by a fake below, there is
# no graphics driver involved.  In production the probe runs in a child process
# (a graphics backend can abort the whole process).
os.environ["OPENGATE_VISU_PROBE_INPROCESS"] = "1"


def fake_probe(available):
    """Replacement for visualization.probe_rendering()."""

    def probe(only=None):
        reports = []
        for rung in visu.BACKENDS:
            if rung in available:
                reports.append(
                    {
                        "backend": rung,
                        "available": True,
                        "api": visu._WEBGPU_RUNGS.get(rung, "opengl2").lower(),
                        "vendor": "Test Vendor",
                        "renderer": f"Test {rung} renderer",
                        "version": "1.0",
                        "device_index": 0 if rung == "cuda" else -1,
                        "render_ms": 1.0,
                        "blank": False,
                    }
                )
            else:
                reports.append(
                    {"backend": rung, "available": False, "reason": f"no {rung}"}
                )
        return reports

    return probe


def with_probe(available, function):
    original = visu.probe_rendering
    visu.probe_rendering = fake_probe(available)
    visu._BACKEND_CACHE.clear()
    try:
        return function()
    finally:
        visu.probe_rendering = original
        visu._BACKEND_CACHE.clear()


if __name__ == "__main__":
    is_ok = True

    b = visu.BACKENDS == ("cuda", "vulkan", "metal", "gpu", "cpu")
    utility.print_test(b, f"Ladder order is {visu.BACKENDS}")
    is_ok = is_ok and b

    # auto: first usable rung, the skipped ones are reported
    info = with_probe({"gpu", "cpu"}, lambda: visu.resolve_backend("auto"))
    b = info.backend == "gpu" and set(info.skipped) == {"cuda", "vulkan", "metal"}
    utility.print_test(b, f"auto picks the first usable rung: {info.report()}")
    is_ok = is_ok and b

    # auto with everything available: cuda wins (an NVIDIA card was found)
    info = with_probe(visu.BACKENDS, lambda: visu.resolve_backend("auto"))
    b = info.backend == "cuda" and info.device_index == 0
    utility.print_test(b, f"auto prefers cuda when it is usable: {info.summary()}")
    is_ok = is_ok and b

    # auto falls back to the cpu when there is no GPU
    info = with_probe({"cpu"}, lambda: visu.resolve_backend("auto"))
    b = info.backend == "cpu"
    utility.print_test(b, f"auto falls back to cpu: {info.summary()}")
    is_ok = is_ok and b

    # an explicit backend is exactly what is asked, never a downgrade
    info = with_probe({"gpu", "cpu"}, lambda: visu.resolve_backend("cpu"))
    b = info.backend == "cpu"
    utility.print_test(b, "explicit 'cpu' is honoured")
    is_ok = is_ok and b

    # an explicit unusable backend raises, with the reason
    def raise_vulkan():
        visu.resolve_backend("vulkan")

    try:
        with_probe({"gpu"}, raise_vulkan)
        b = False
    except visu.VisuBackendError as exception:
        b = "not usable" in str(exception) and "no vulkan" in str(exception)
    utility.print_test(b, "explicit 'vulkan' fails loudly, with the reason")
    is_ok = is_ok and b

    # no usable backend at all
    def raise_auto():
        visu.resolve_backend("auto")

    try:
        with_probe(set(), raise_auto)
        b = False
    except visu.VisuBackendError as exception:
        b = "No VTK backend is usable" in str(exception)
    utility.print_test(
        b, "a machine with no usable backend gets an error, not a window"
    )
    is_ok = is_ok and b

    # unknown backend name
    try:
        visu.resolve_backend("cuda-opengl")
        b = False
    except visu.VisuBackendError as exception:
        b = "Unknown VTK backend" in str(exception)
    utility.print_test(b, "an unknown backend name is refused")
    is_ok = is_ok and b

    # environment variable, used when the argument is 'auto'
    def from_env():
        os.environ["OPENGATE_VISU_BACKEND"] = "cpu"
        try:
            return visu.resolve_backend("auto")
        finally:
            del os.environ["OPENGATE_VISU_BACKEND"]

    info = with_probe({"gpu", "cpu"}, from_env)
    b = info.backend == "cpu" and info.requested == "cpu"
    utility.print_test(b, "OPENGATE_VISU_BACKEND overrides 'auto'")
    is_ok = is_ok and b

    # the resolution is cached: the probe runs once per process
    calls = []

    def counting_probe():
        original = visu.probe_rendering
        visu.probe_rendering = fake_probe({"gpu"})

        def counted(only=None):
            calls.append(1)
            return (
                visu.probe_rendering.__wrapped__(only)
                if hasattr(visu.probe_rendering, "__wrapped__")
                else fake_probe({"gpu"})(only)
            )

        visu.probe_rendering = counted
        try:
            visu.resolve_backend("auto")
            visu.resolve_backend("auto")
            visu.resolve_backend("auto")
        finally:
            visu.probe_rendering = original
            visu._BACKEND_CACHE.clear()
        return len(calls)

    b = counting_probe() == 1
    utility.print_test(b, "the backend probe is cached (1 probe for 3 resolutions)")
    is_ok = is_ok and b

    utility.test_ok(is_ok)
