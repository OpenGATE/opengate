#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Benchmark of the opengate visualisation drivers: VTK against the others.

Every driver is measured end to end, on the same scene:

======== ==========================================================================
driver   what is timed
======== ==========================================================================
vrml     Geant4 VRML2FILE export, then the pyvista viewer (the default today)
gdml     Geant4 GDML export, then the pyg4ometry viewer
vtk      Geant4 VRML2FILE export, then the VTK driver (visu_type = 'vtk')
qt       the Geant4 Qt viewer: a GUI event loop, reported but not timed
======== ==========================================================================

The export runs in its own process (the Geant4 kernel can only be initialised
once per process), each viewer runs in its own process too (VTK, pyvista and
pyg4ometry must not share a render window, and the peak memory has to be
attributable to one viewer).

Usage::

    opengate_visu_benchmark --generate                 # demo scene, full report
    opengate_visu_benchmark --vrml scene.wrl --gdml scene.gdml --slices s.npz
    opengate_visu_benchmark --generate --frames 60 --json report.json --markdown report.md

``--generate`` writes the scene, benchmarks every viewer and prints the table;
without it, the benchmark runs on the files you provide.
"""

import json
import os
import platform
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import click

VIEWERS = ("vtk", "pyvista", "pyg4ometry", "qt")
_JSON_PREFIX = "BENCH_JSON:"


# -----------------------------------------------------------------------------
# Where the numbers come from
# -----------------------------------------------------------------------------
def _peak_rss_mb():
    """Peak resident memory of this process, in MB."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux kilobytes
    return value / (1024 * 1024) if sys.platform == "darwin" else value / 1024


def _timed(function, repeat=1):
    """Run a function, return (seconds, result) with the best of `repeat`."""
    best = float("inf")
    result = None
    for _ in range(repeat):
        t0 = time.perf_counter()
        result = function()
        best = min(best, time.perf_counter() - t0)
    return best, result


def _frame_times(render, frames):
    """Median/p95/min frame time of `frames` renders, in ms."""
    times = []
    for _ in range(frames):
        t0 = time.perf_counter()
        render()
        times.append(1000.0 * (time.perf_counter() - t0))
    times.sort()
    return {
        "frame_median_ms": round(times[len(times) // 2], 2),
        "frame_min_ms": round(times[0], 2),
        "frame_p95_ms": round(times[max(0, int(0.95 * len(times)) - 1)], 2),
        "frames": frames,
    }


def _scene_stats(renderer):
    """Number of props and of triangles of a VTK renderer."""
    props = renderer.GetViewProps().GetNumberOfItems()
    triangles = 0
    try:
        for i in range(props):
            prop = renderer.GetViewProps().GetItemAsObject(i)
            mapper = getattr(prop, "GetMapper", lambda: None)()
            data = mapper.GetInput() if mapper is not None else None
            if data is not None and hasattr(data, "GetNumberOfPolys"):
                triangles += data.GetNumberOfPolys()
    except Exception:
        pass
    return {"props": props, "triangles": triangles}


# -----------------------------------------------------------------------------
# geant4 export (one process per export)
# -----------------------------------------------------------------------------
_THUMBNAIL_IMAGE = None


def build_simulation(paths, visu_type, filename, screenshot=None, with_image=False):
    """The benchmark scene: a water box, a ring of spheres, an image volume."""
    import numpy as np

    import opengate as gate

    sim = gate.Simulation()
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = visu_type
    sim.visu_filename = str(filename)
    sim.visu_screenshot = screenshot
    sim.number_of_threads = 1
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 1234

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    sim.world.size = [2 * m, 2 * m, 2 * m]

    water = sim.add_volume("Box", "Waterbox")
    water.size = [40 * cm, 40 * cm, 40 * cm]
    water.material = "G4_WATER"
    water.color = (0.2, 0.6, 1.0, 1.0)

    # a ring of 12 spheres coloured like a PET block detector
    for i in range(12):
        angle = 2 * np.pi * i / 12
        sphere = sim.add_volume("Sphere", f"sphere_{i}")
        sphere.rmin = 2 * cm
        sphere.rmax = 5 * cm
        sphere.translation = [60 * cm * np.cos(angle), 60 * cm * np.sin(angle), 0]
        sphere.material = "G4_LEAD_OXIDE"
        sphere.color = (1.0, 0.4 * i / 12, 0.2, 1.0)

    if with_image:
        image_file = Path(paths) / "benchmark_image.mha"
        if not image_file.is_file():
            _write_thumbnail_image(image_file)
        patient = sim.add_volume("Image", "patient")
        patient.image = str(image_file)
        patient.material = "G4_AIR"
        patient.voxel_materials = [
            [-2000, -200, "G4_AIR"],
            [-200, 300, "G4_WATER"],
            [300, 20000, "G4_BONE_COMPACT_ICRU"],
        ]
        # below the water box (which spans z = +-20 cm), not inside it
        patient.translation = [0, 0, -50 * cm]
        patient.visu_window = [-200, 800]

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 100 * gate.g4_units.keV
    source.direction.type = "iso"
    source.activity = 200 * gate.g4_units.Bq
    source.position.type = "point"
    source.position.translation = [0, 0, 0]

    # a few primaries only: the benchmark measures the visualisation, not physics
    sim.run_timing_intervals = [[0, 0.02 * gate.g4_units.s]]
    sim.add_actor("SimulationStatisticsActor", "Stats")
    return sim


def _write_thumbnail_image(filename):
    """A synthetic CT-like image (no data download needed for the benchmark)."""
    import itk
    import numpy as np

    n = 64
    array = np.zeros((n, n, n), dtype=np.int16)
    zz, yy, xx = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing="ij")
    centre = (n - 1) / 2
    radius = np.sqrt((xx - centre) ** 2 + (yy - centre) ** 2 + (zz - centre) ** 2)
    array[radius < n * 0.4] = -500  # air
    array[radius < n * 0.3] = 0  # water
    array[radius < n * 0.15] = 1000  # bone
    image = itk.image_from_array(array)
    image.SetSpacing([4.0, 4.0, 4.0])
    itk.imwrite(image, str(filename))


def export_scene(kind, outdir, with_image=False, backend="auto"):
    """Build the scene and export it. Runs in its own process."""
    import opengate_core as g4

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    result = {"export": kind, "with_image": with_image}

    if kind == "gdml" and not g4.GateInfo.get_G4GDML():
        return {
            **result,
            "seconds": 0.0,
            "error": "Geant4 is compiled without GDML (USE_GDML=0 in this "
            "opengate_core): the gdml driver cannot be benchmarked here",
        }

    if kind == "vrml":
        filename = outdir / "benchmark.wrl"
        sim = build_simulation(
            outdir, "vrml_file_only", filename, with_image=with_image
        )
    elif kind == "gdml":
        filename = outdir / "benchmark.gdml"
        sim = build_simulation(
            outdir, "gdml_file_only", filename, with_image=with_image
        )
    elif kind == "vk":
        filename = outdir / "benchmark_vtk.wrl"
        sim = build_simulation(
            outdir,
            "vtk",
            filename,
            screenshot=str(outdir / "benchmark_vtk.png"),
            with_image=with_image,
        )
        sim.visu_backend = backend
    elif kind == "qt":
        filename = outdir / "benchmark_qt.wrl"
        sim = build_simulation(outdir, "qt", filename, with_image=with_image)
    else:
        raise ValueError(f"unknown export kind '{kind}'")

    t0 = time.perf_counter()
    sim.run(start_new_process=False)
    result["seconds"] = time.perf_counter() - t0
    result["files"] = sorted(
        str(p)
        for p in outdir.iterdir()
        if p.suffix in (".wrl", ".gdml", ".npz", ".png")
    )
    result["wrl"] = str(outdir / "benchmark.wrl")
    result["gdml"] = str(outdir / "benchmark.gdml")
    return result


def _run_export(kind, outdir, with_image, backend="auto", timeout=900):
    """Run export_scene() in a child process and read its JSON report."""
    code = (
        "import json, sys\n"
        "from opengate.bin.opengate_visu_benchmark import export_scene\n"
        f"r = export_scene({kind!r}, {str(outdir)!r}, {with_image!r}, {backend!r})\n"
        f"print({_JSON_PREFIX!r} + json.dumps(r))\n"
    )
    t0 = time.perf_counter()
    process = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout
    )
    wall = time.perf_counter() - t0
    if process.returncode != 0:
        raise RuntimeError(
            f"the '{kind}' export failed (return code {process.returncode}):\n"
            f"{process.stdout[-2000:]}\n{process.stderr[-2000:]}"
        )
    for line in process.stdout.splitlines():
        if line.startswith(_JSON_PREFIX):
            report = json.loads(line[len(_JSON_PREFIX) :])
            report["wall_seconds"] = wall
            return report
    raise RuntimeError(
        f"no benchmark report from the '{kind}' export:\n{process.stdout[-2000:]}"
    )


# -----------------------------------------------------------------------------
# viewer benchmarks (one process per viewer)
# -----------------------------------------------------------------------------
def bench_vtk(vrml, slices=None, frames=30, size=(1024, 768), backend="auto"):
    from opengate import visualization

    # the backend probe is a one-off (cached for the process): time it apart,
    # it is not part of the scene loading
    probe_s, info = _timed(lambda: visualization.resolve_backend(backend))
    load_s, (info, window, renderer) = _timed(
        lambda: visualization.build_scene(
            vrml, backend=backend, slices=slices, size=size, offscreen=True
        )
    )
    first_s, _ = _timed(window.Render)
    frames_report = _frame_times(window.Render, frames)
    shot_s, _ = _timed(
        lambda: visualization._write_screenshot(
            visualization.import_vtk(),
            window,
            str(Path(vrml).with_suffix(".bench.png")),
        )
    )
    result = {
        "viewer": "vtk",
        "available": True,
        "backend": info.report(),
        "probe_ms": round(1000 * probe_s, 2),
        "load_ms": round(1000 * load_s, 2),
        "first_frame_ms": round(1000 * first_s, 2),
        "screenshot_ms": round(1000 * shot_s, 2),
        "screenshot": str(Path(vrml).with_suffix(".bench.png")),
        **_scene_stats(renderer),
        **frames_report,
    }
    window.Finalize()
    return result


def bench_pyvista(vrml, frames=30, size=(1024, 768)):
    try:
        import pyvista
    except Exception as exception:
        return {"viewer": "pyvista", "available": False, "reason": str(exception)}

    pyvista.OFF_SCREEN = True

    def load():
        plotter = pyvista.Plotter(off_screen=True, window_size=list(size))
        plotter.import_vrml(str(vrml))
        plotter.set_background("black")
        plotter.add_axes(line_width=5)
        return plotter

    try:
        load_s, plotter = _timed(load)
        # plotter.render() is a no-op when nothing changed: time the underlying
        # render window, exactly like the VTK driver, so the frames compare
        render = plotter.ren_win.Render
        first_s, _ = _timed(render)
        frames_report = _frame_times(render, frames)
        png = str(Path(vrml).with_suffix(".bench_pyvista.png"))
        shot_s, _ = _timed(lambda: plotter.screenshot(png))
        renderer = plotter.renderer
        result = {
            "viewer": "pyvista",
            "available": True,
            "backend": f"pyvista {pyvista.__version__}",
            "load_ms": round(1000 * load_s, 2),
            "first_frame_ms": round(1000 * first_s, 2),
            "screenshot_ms": round(1000 * shot_s, 2),
            "screenshot": png,
            **_scene_stats(renderer),
            **frames_report,
        }
        plotter.close()
        return result
    except Exception as exception:
        return {"viewer": "pyvista", "available": False, "reason": str(exception)}


def bench_pyg4ometry(gdml, frames=30, size=(1024, 768)):
    try:
        import pyg4ometry
    except Exception as exception:
        return {"viewer": "pyg4ometry", "available": False, "reason": str(exception)}
    if gdml is None:
        return {
            "viewer": "pyg4ometry",
            "available": False,
            "reason": "no GDML file (use --gdml or --generate)",
        }

    def load():
        reader = pyg4ometry.gdml.Reader(str(gdml))
        viewer = pyg4ometry.visualisation.VtkViewerColouredMaterial()
        viewer.addLogicalVolume(reader.getRegistry().getWorldVolume())
        viewer.renWin.SetSize(*size)
        viewer.renWin.SetOffScreenRendering(1)
        return viewer

    try:
        load_s, viewer = _timed(load)
        render = viewer.renWin.Render
        first_s, _ = _timed(render)
        frames_report = _frame_times(render, frames)
        from opengate.visualization import import_vtk, _write_screenshot

        vtk = import_vtk()
        png = str(Path(gdml).with_suffix(".bench_pyg4ometry.png"))
        shot_s, _ = _timed(lambda: _write_screenshot(vtk, viewer.renWin, png))
        return {
            "viewer": "pyg4ometry",
            "available": True,
            "backend": f"pyg4ometry {getattr(pyg4ometry, '__version__', '?')}",
            "load_ms": round(1000 * load_s, 2),
            "first_frame_ms": round(1000 * first_s, 2),
            "screenshot_ms": round(1000 * shot_s, 2),
            "screenshot": png,
            **_scene_stats(viewer.ren),
            **frames_report,
        }
    except Exception as exception:
        return {"viewer": "pyg4ometry", "available": False, "reason": str(exception)}


def _run_viewer(
    viewer, vrml, gdml, slices, frames, size=(1024, 768), backend="auto", timeout=900
):
    needed = [] if viewer == "pyg4ometry" else [vrml]
    if viewer == "pyg4ometry":
        needed = [gdml]
    for filename in needed:
        if not filename or not Path(filename).is_file():
            return {
                "viewer": viewer,
                "available": False,
                "reason": f"missing file: {filename}",
            }
    code = (
        "import json, sys\n"
        "from opengate.bin.opengate_visu_benchmark import _bench_viewer\n"
        f"r = _bench_viewer({viewer!r}, {vrml!r}, {gdml!r}, {slices!r}, {frames},"
        f" {tuple(size)!r}, {backend!r})\n"
        f"print({_JSON_PREFIX!r} + json.dumps(r))\n"
    )
    process = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout
    )
    if process.returncode != 0:
        return {
            "viewer": viewer,
            "available": False,
            "reason": (
                process.stderr.strip().splitlines()[-1] if process.stderr else "crashed"
            ),
        }
    for line in process.stdout.splitlines():
        if line.startswith(_JSON_PREFIX):
            return json.loads(line[len(_JSON_PREFIX) :])
    return {"viewer": viewer, "available": False, "reason": "no report"}


def _bench_viewer(viewer, vrml, gdml, slices, frames, size=(1024, 768), backend="auto"):
    """One viewer, in its own process (see the module docstring)."""
    t0 = time.perf_counter()
    if viewer == "vtk":
        result = bench_vtk(
            vrml, slices=slices, frames=frames, size=size, backend=backend
        )
    elif viewer == "pyvista":
        result = bench_pyvista(vrml, frames=frames, size=size)
    elif viewer == "pyg4ometry":
        result = bench_pyg4ometry(gdml, frames=frames, size=size)
    else:
        raise ValueError(f"unknown viewer '{viewer}'")
    result["total_seconds"] = time.perf_counter() - t0
    result["peak_rss_mb"] = round(_peak_rss_mb(), 1)
    return result


def bench_qt(outdir, with_image):
    """The Geant4 Qt viewer: reported, never timed (GUI event loop)."""
    return {
        "viewer": "qt",
        "available": False,
        "reason": (
            "the Geant4 Qt driver opens an interactive window and waits for the "
            "user: it has no offscreen mode and cannot be timed automatically. "
            "Its Geant4-side cost is the geometry traversal, shared with the "
            "VRML export measured here."
        ),
    }


# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------
def _table(rows, columns):
    widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(row.get(c, ""))))
    lines = ["| " + " | ".join(c.ljust(widths[c]) for c in columns) + " |"]
    lines.append("|" + "|".join("-" * (widths[c] + 2) for c in columns) + "|")
    for row in rows:
        lines.append(
            "| "
            + " | ".join(str(row.get(c, "")).ljust(widths[c]) for c in columns)
            + " |"
        )
    return "\n".join(lines)


# which Geant4 export belongs to which viewer (the export is what the driver
# writes before its viewer runs)
_EXPORT_OF = {"vtk": "vtk", "pyvista": "vrml", "pyg4ometry": "gdml", "qt": None}


def build_report(export_seconds, viewers, image_volume):
    rows = []
    for viewer in VIEWERS:
        entry = viewers.get(
            viewer, {"viewer": viewer, "available": False, "reason": "?"}
        )
        row = {"driver": viewer, "status": "ok" if entry.get("available") else "n/a"}
        if entry.get("available"):
            key = _EXPORT_OF.get(viewer)
            export = export_seconds.get(key, {}).get("seconds", 0.0) if key else 0.0
            row.update(
                {
                    "sim+export s": f"{export:.2f}",
                    "load ms": f"{entry['load_ms']:.0f}",
                    "first frame ms": f"{entry['first_frame_ms']:.0f}",
                    "frame ms (median)": f"{entry['frame_median_ms']:.1f}",
                    "frame ms (p95)": f"{entry['frame_p95_ms']:.1f}",
                    "screenshot ms": f"{entry['screenshot_ms']:.0f}",
                    "peak RSS MB": f"{entry.get('peak_rss_mb', 0):.0f}",
                    "props": entry.get("props", ""),
                    "triangles": entry.get("triangles", ""),
                    "backend": entry.get("backend", ""),
                }
            )
            row["end-to-end s"] = (
                f"{export + entry['load_ms'] / 1000 + entry['first_frame_ms'] / 1000:.2f}"
            )
        else:
            row["backend"] = str(entry.get("reason", ""))[:60]
        rows.append(row)

    columns = [
        "driver",
        "status",
        "sim+export s",
        "load ms",
        "first frame ms",
        "frame ms (median)",
        "frame ms (p95)",
        "screenshot ms",
        "peak RSS MB",
        "props",
        "triangles",
        "end-to-end s",
        "backend",
    ]
    title = (
        f"opengate visualisation benchmark - {platform.platform()}, "
        f"{'with' if image_volume else 'without'} image volume"
    )
    return title, _table(rows, columns)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--vrml", default="", help="VRML file to display (all viewers except pyg4ometry)"
)
@click.option("--gdml", default="", help="GDML file (pyg4ometry viewer)")
@click.option("--slices", default="", help=".npz image slices for the VTK viewer")
@click.option(
    "--generate",
    "generate_dir",
    default="",
    help="build a demo scene in this directory, export it and benchmark everything",
)
@click.option("--with-image", is_flag=True, help="with --generate: add an image volume")
@click.option(
    "--frames", default=30, help="number of frames for the frame-time statistics"
)
@click.option(
    "--backend", default="auto", help="VTK backend: auto, cuda, vulkan, gpu, cpu"
)
@click.option("--size", default="1024x768", help="render size, e.g. 1024x768")
@click.option(
    "--json", "json_out", default="", help="write the raw report to this JSON file"
)
@click.option(
    "--markdown", default="", help="write the report table to this markdown file"
)
@click.option(
    "--viewer",
    default="",
    help="internal: benchmark a single viewer (used for the per-viewer subprocesses)",
)
@click.option(
    "--export",
    "export_kind",
    default="",
    help="internal: export the demo scene only (vrml, gdml, vk, qt)",
)
def go(
    vrml,
    gdml,
    slices,
    generate_dir,
    with_image,
    frames,
    backend,
    size,
    json_out,
    markdown,
    viewer,
    export_kind,
):
    width, height = (int(v) for v in size.lower().split("x"))

    # internal modes, used by the subprocesses of this script
    if export_kind:
        print(
            _JSON_PREFIX
            + json.dumps(
                export_scene(export_kind, tempfile.gettempdir(), with_image, backend)
            )
        )
        return 0
    if viewer:
        print(
            _JSON_PREFIX
            + json.dumps(
                _bench_viewer(
                    viewer,
                    vrml,
                    gdml or None,
                    slices or None,
                    frames,
                    (width, height),
                    backend,
                )
            )
        )
        return 0

    exports = {}
    image_volume = with_image
    if generate_dir:
        outdir = Path(generate_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"generating the demo scene in {outdir} ...")
        for kind, name in (("vrml", "vrml"), ("gdml", "gdml"), ("vk", "vtk")):
            print(f"  export '{kind}' ...")
            try:
                exports[name] = _run_export(kind, outdir, with_image, backend)
                if exports[name].get("error"):
                    print(f"    not available: {exports[name]['error']}")
                else:
                    print(f"    {exports[name]['seconds']:.2f} s")
            except Exception as exception:
                print(f"    failed: {exception}")
                exports[name] = {"seconds": 0.0}
        vrml = vrml or str(outdir / "benchmark.wrl")
        gdml = gdml or str(outdir / "benchmark.gdml")
        slices = slices or str(outdir / "benchmark_vtk.wrl.slices.npz")
        if not Path(slices).is_file():
            slices = ""
        image_volume = with_image and bool(slices)

    if not vrml:
        print("nothing to benchmark: pass --vrml and/or --gdml, or --generate DIR")
        return 1

    print(f"benchmarking the viewers ({frames} frames each) ...")
    viewers = {}
    for name in ("vtk", "pyvista", "pyg4ometry"):
        print(f"  {name} ...")
        viewers[name] = _run_viewer(
            name,
            vrml,
            gdml or None,
            slices or None,
            frames,
            (width, height),
            backend,
        )
        if not viewers[name].get("available"):
            print(f"    not available: {viewers[name].get('reason')}")
    viewers["qt"] = bench_qt(generate_dir, with_image)

    title, table = build_report(exports, viewers, image_volume)
    text = f"{title}\n\n{table}\n"
    print("\n" + text)

    if json_out:
        Path(json_out).write_text(
            json.dumps(
                {"title": title, "exports": exports, "viewers": viewers}, indent=2
            )
        )
        print(f"raw report: {json_out}")
    if markdown:
        Path(markdown).write_text(f"# {title}\n\n{table}\n")
        print(f"report table: {markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(go())
