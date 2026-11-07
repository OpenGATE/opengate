#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the opt-in VTK visualisation (visu_type = 'vtk'):

- the simulation runs and writes the VRML scene that the viewer renders;
- the scene is rendered by VTK (offscreen, from a screenshot request), and the
  screenshot is not blank: the geometry, its colours and the trajectories are
  there;
- the slices of an image volume are handed over to the viewer, and the VTK
  scene contains the image box, its three slices and their outlines;
- the same scene is rendered with an explicit backend.

The VTK viewer is skipped (not failed) when the optional vtk package is not
installed: vtk is not a dependency of opengate.
"""

import numpy as np

import opengate as gate
from opengate.tests import utility


def is_vtk_available():
    try:
        import vtk  # noqa: F401

        return True
    except Exception:
        return False


def create_simulation(paths, visu_type="vtk", screenshot=None, with_image=True):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = True
    sim.visu_type = visu_type
    sim.visu_filename = str(paths.output / "test004_vtk.wrl")
    sim.visu_screenshot = screenshot
    sim.visu_verbose = False
    sim.number_of_threads = 1
    sim.random_engine = "MersenneTwister"
    sim.random_seed = "auto"

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    sim.world.size = [3 * m, 3 * m, 3 * m]

    waterbox = sim.add_volume("Box", "Waterbox")
    waterbox.size = [40 * cm, 40 * cm, 40 * cm]
    waterbox.translation = [0 * cm, 0 * cm, 25 * cm]
    waterbox.material = "G4_WATER"
    waterbox.color = (0.2, 0.6, 1.0, 1.0)

    if with_image:
        patient = sim.add_volume("Image", "patient")
        patient.image = paths.data / "patient-4mm.mhd"
        patient.material = "G4_AIR"
        patient.voxel_materials = [
            [-2000, -200, "G4_AIR"],
            [-200, 300, "G4_WATER"],
            [300, 20000, "G4_BONE_COMPACT_ICRU"],
        ]
        patient.visu_window = [-200, 800]
        # beside the water box, not inside it
        patient.translation = [0 * cm, 0 * cm, -25 * cm]

    keV = gate.g4_units.keV
    Bq = gate.g4_units.Bq
    source = sim.add_source("GenericSource", "Default")
    source.particle = "gamma"
    source.energy.mono = 80 * keV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.activity = 200 * Bq

    sec = gate.g4_units.second
    sim.run_timing_intervals = [[0, 0.5 * sec], [0.5 * sec, 1.0 * sec]]
    sim.add_actor("SimulationStatisticsActor", "Stats")
    return sim


def image_std(filename):
    """Standard deviation of a screenshot, 0 for a blank image."""
    import itk

    image = itk.GetArrayFromImage(itk.imread(str(filename)))
    return float(np.asarray(image).std())


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

    is_ok = True

    # ---------------------------------------------------------------- probe
    info = visualization.resolve_backend("auto")
    b = info.backend in visualization.BACKENDS and bool(info.renderer)
    utility.print_test(b, f"backend resolved: {info.report()}")
    is_ok = is_ok and b

    # ------------------------------------------------------------- rendering
    screenshot = paths.output / "test004_vtk.png"
    screenshot.unlink(missing_ok=True)
    vrml = paths.output / "test004_vtk.wrl"
    vrml.unlink(missing_ok=True)

    sim = create_simulation(paths, screenshot=screenshot)
    sim.run(start_new_process=False)

    b = vrml.is_file() and vrml.stat().st_size > 0
    utility.print_test(b, f"the VRML scene was written: {vrml.name}")
    is_ok = is_ok and b

    b = screenshot.is_file() and screenshot.stat().st_size > 0
    utility.print_test(b, f"the screenshot was written: {screenshot.name}")
    is_ok = is_ok and b

    std = image_std(screenshot) if b else 0.0
    b = std > 5.0
    utility.print_test(b, f"the screenshot is not blank (std = {std:.1f})")
    is_ok = is_ok and b

    # the slices of the image volume were handed over to the viewer
    slices_file = str(vrml) + ".slices.npz"
    b = vrml.is_file()
    from pathlib import Path

    slices = Path(slices_file)
    b = slices.is_file()
    utility.print_test(b, f"the image slices were handed over to VTK: {slices.name}")
    if b:
        data = visualization.load_slices(slices_file)
        b = len(data) == 1 and data[0]["name"] == "patient"
        nx, ny, nz = (int(v) for v in data[0]["size"])
        b = b and nx > 0 and ny > 0 and nz > 0
        b = b and len(data[0]["slice_xy"]) == nx * ny
        b = b and len(data[0]["slice_xz"]) == nx * nz
        b = b and len(data[0]["slice_yz"]) == ny * nz
        b = b and min(data[0]["slice_xy"]) >= 0 and max(data[0]["slice_xy"]) <= 1
        utility.print_test(b, "one image volume, windowed in [0, 1]")
        is_ok = is_ok and b

    # ------------------------------------------------------- explicit backend
    screenshot2 = paths.output / "test004_vtk_cpu.png"
    screenshot2.unlink(missing_ok=True)
    try:
        info2 = visualization.show(
            vrml,
            backend="cpu",
            screenshot=screenshot2,
            slices=slices_file if slices.is_file() else None,
        )
        b = screenshot2.is_file() and image_std(screenshot2) > 5.0
        utility.print_test(
            b, f"explicit 'cpu' backend renders offscreen: {info2.summary()}"
        )
    except visualization.VisuBackendError as exception:
        print(f"explicit 'cpu' is not available on this machine: {exception}")
        b = True
    is_ok = is_ok and b

    # --------------------------------------------- the scene has the slices
    # the three slices and their outlines are added to the VTK scene, on top
    # of the volumes of the VRML export
    from opengate.visualization import add_slices

    vtk = visualization.import_vtk()
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    _, renderer = visualization.import_vrml(window, vrml)
    props_before = renderer.GetViewProps().GetNumberOfItems()
    added = (
        add_slices(renderer, visualization.load_slices(slices_file))
        if slices.is_file()
        else 0
    )
    b = added == 3 and renderer.GetViewProps().GetNumberOfItems() == props_before + 6
    utility.print_test(
        b, f"3 slices and 3 outlines added to the scene ({added} slices)"
    )
    is_ok = is_ok and b
    window.Finalize()

    utility.test_ok(is_ok)
