#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the .vtp scene cache of the VTK visualisation driver:

- with an OpenGL2 backend, the first open parses the VRML and writes a baked
  .vtp beside it, smaller than the VRML it comes from; the next open reads that
  file as a single actor and draws the same pixels;
- with a WebGPU backend the cache is not used at all: vtkWebGPU draws no pixel
  of a polydata coloured by an array, so the scene is parsed every time (see
  the plan, section 6.4);
- a newer VRML invalidates the cache, and OPENGATE_VISU_CACHE=0 turns it off.

Anything that needs the actors of the scene (per-track animation, per-volume
visibility, edges=True) asks for cache=False; that is checked too.

Skipped (not failed) when vtk is missing or no backend is usable: vtk is an
optional dependency of opengate.
"""

import os
import shutil

import numpy as np

import opengate as gate
from opengate.tests import utility


def is_vtk_available():
    try:
        import vtk  # noqa: F401

        return True
    except Exception:
        return False


def create_simulation(paths, vrml):
    """A grid of boxes: enough geometry for the cache to pay for itself."""
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = "vrml_file_only"
    sim.visu_filename = str(vrml)
    sim.visu_verbose = False
    sim.number_of_threads = 1
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 1

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    sim.world.size = [1 * m, 1 * m, 1 * m]
    n = 6
    for i in range(n):
        for j in range(n):
            for k in range(n):
                box = sim.add_volume("Box", f"box_{i}_{j}_{k}")
                box.size = [3 * cm, 3 * cm, 3 * cm]
                box.translation = [
                    (i - (n - 1) / 2) * 8 * cm,
                    (j - (n - 1) / 2) * 8 * cm,
                    (k - (n - 1) / 2) * 8 * cm,
                ]
                box.material = "G4_WATER"
                box.color = (i / n, j / n, 0.9, 1.0)

    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 100 * gate.g4_units.keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 100 * gate.g4_units.Bq
    sim.run_timing_intervals = [[0, 0.01 * gate.g4_units.s]]
    return sim


def pixels(filename):
    import itk

    return np.asarray(itk.GetArrayFromImage(itk.imread(str(filename))), dtype=float)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(
        __file__, "gate_test004_simulation_stats_actor"
    )

    if not is_vtk_available():
        print(
            "SKIPPED: the optional vtk package is not installed.\n"
            "Install it with: pip install vtk   (or: pip install 'opengate[vtk]')"
        )
        utility.test_ok(True)
        raise SystemExit(0)

    from opengate import visualization

    try:
        visualization.resolve_backend("auto")
    except visualization.VisuBackendError as exception:
        print(f"SKIPPED: no usable VTK backend on this machine: {exception}")
        utility.test_ok(True)
        raise SystemExit(0)

    is_ok = True
    vrml = paths.output / "test004_cache.wrl"
    cache = vrml.with_suffix(".vtp")
    parsed_png = paths.output / "test004_cache_parsed.png"
    read_png = paths.output / "test004_cache_read.png"
    for filename in (vrml, cache, parsed_png, read_png):
        filename.unlink(missing_ok=True)

    sim = create_simulation(paths, vrml)
    sim.run(start_new_process=False)

    b = vrml.is_file() and vrml.stat().st_size > 0 and not cache.exists()
    utility.print_test(b, f"the VRML scene is written, with no cache yet: {vrml.name}")
    is_ok = is_ok and b

    vtk = visualization.import_vtk()
    size = (320, 240)

    # the reference: the VRML parsed, cache bypassed
    info, window, renderer = visualization.build_scene(
        str(vrml), cache=False, offscreen=True, size=size
    )
    props_parsed = renderer.GetViewProps().GetNumberOfItems()
    webgpu = "webgpu" in window.GetClassName().lower()
    # twice: the first frame of an offscreen window can still be incomplete
    window.Render()
    window.Render()
    visualization._write_screenshot(vtk, window, parsed_png)
    window.Finalize()
    b = props_parsed > 3 and not cache.exists()
    utility.print_test(
        b, f"cache=False parses the scene ({props_parsed} actors) and writes no cache"
    )
    is_ok = is_ok and b
    print(f"backend: {info.summary()} ({window.GetClassName()})")

    if webgpu:
        # documented in the plan: vtkWebGPU cannot draw the baked polydata, so
        # the cache stays out of the way instead of showing an empty window
        info, window, renderer = visualization.build_scene(
            str(vrml), offscreen=True, size=size
        )
        props_default = renderer.GetViewProps().GetNumberOfItems()
        window.Render()
        window.Render()
        window.Finalize()
        b = props_default == props_parsed and not cache.exists()
        utility.print_test(
            b,
            "a WebGPU backend parses the scene instead of using the cache "
            f"({props_default} actors, no {cache.name})",
        )
        is_ok = is_ok and b
    else:
        # the first default open: parses, draws, and leaves the cache behind
        info, window, renderer = visualization.build_scene(
            str(vrml), offscreen=True, size=size
        )
        window.Render()
        window.Render()
        window.Finalize()
        b = cache.is_file()
        utility.print_test(
            b,
            f"the first open wrote {cache.name} "
            f"({cache.stat().st_size // 1024} KB against {vrml.stat().st_size // 1024} KB)",
        )
        is_ok = is_ok and b
        b = cache.is_file() and cache.stat().st_size < vrml.stat().st_size
        utility.print_test(b, "the cache is smaller than the VRML it comes from")
        is_ok = is_ok and b

        # the second open reads it: one actor, same pixels
        info, window, renderer = visualization.build_scene(
            str(vrml), offscreen=True, size=size
        )
        props_cached = renderer.GetViewProps().GetNumberOfItems()
        window.Render()
        window.Render()
        visualization._write_screenshot(vtk, window, read_png)
        window.Finalize()
        b = props_cached < props_parsed
        utility.print_test(
            b,
            f"the cached scene is one actor ({props_cached} props against {props_parsed})",
        )
        is_ok = is_ok and b

        if parsed_png.is_file() and read_png.is_file():
            parsed, read = pixels(parsed_png), pixels(read_png)
            b = parsed.shape == read.shape and np.allclose(parsed, read, atol=1)
            delta = (
                float(np.abs(parsed - read).max())
                if parsed.shape == read.shape
                else float("nan")
            )
            utility.print_test(
                b, f"the cached frame matches the parsed one (max delta {delta})"
            )
        else:
            b = False
            utility.print_test(b, "both screenshots were written")
        is_ok = is_ok and b

    # a newer VRML invalidates the cache (checked on a scratch pair, so this
    # does not depend on which backend wrote a cache above)
    scratch_cache = paths.output / "test004_cache_freshness.vtp"
    scratch_vrml = paths.output / "test004_cache_freshness.wrl"
    shutil.copy(vrml, scratch_vrml)
    scratch_cache.write_bytes(b"baked")
    # explicit times: some filesystems stamp with a 1 s granularity, so "now"
    # cannot be used to order the two files
    source_time = scratch_vrml.stat().st_mtime
    os.utime(scratch_cache, (source_time + 10, source_time + 10))
    b = visualization._cache_is_fresh(scratch_cache, scratch_vrml)
    utility.print_test(b, "a cache newer than its VRML is used")
    is_ok = is_ok and b
    os.utime(scratch_vrml, (source_time + 20, source_time + 20))
    b = not visualization._cache_is_fresh(scratch_cache, scratch_vrml)
    utility.print_test(b, "a newer VRML invalidates the cache")
    is_ok = is_ok and b
    for filename in (scratch_cache, scratch_vrml):
        filename.unlink(missing_ok=True)

    # and the whole thing can be turned off
    os.environ["OPENGATE_VISU_CACHE"] = "0"
    try:
        b = visualization.scene_cache_path(vrml) is None
    finally:
        del os.environ["OPENGATE_VISU_CACHE"]
    utility.print_test(b, "OPENGATE_VISU_CACHE=0 turns the cache off")
    is_ok = is_ok and b

    utility.test_ok(is_ok)
