#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import os
import opengate_core as g4

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input", "-i", default="", help="Input visualization file")
@click.option("--vrml", "-v", is_flag=True, help="VRML file (pyvista viewer)")
@click.option("--gdml", "-g", is_flag=True, help="GDML file (pyg4ometry viewer)")
@click.option(
    "--vtk",
    "use_vtk",
    is_flag=True,
    help="VRML file, rendered with VTK (optional: needs 'pip install vtk')",
)
@click.option("--qt", "-q", is_flag=True, help="Test Qt window")
@click.option(
    "--slices",
    "-s",
    default="",
    help="With --vtk: .npz image slices saved by the simulation",
)
@click.option(
    "--backend",
    "-b",
    default="auto",
    help="With --vtk: auto (default), cuda, vulkan, gpu or cpu",
)
@click.option(
    "--screenshot",
    "-o",
    default="",
    help="With --vtk: save the scene to this image instead of opening a window",
)
@click.option(
    "--probe",
    is_flag=True,
    help="With --vtk: report the graphics backend ladder and exit",
)
def go(input, vrml, gdml, use_vtk, qt, slices, backend, screenshot, probe):

    if qt:
        g4.createTestQtWindow()
        return ()

    if probe:
        from opengate.visualization import main as vtk_main

        return vtk_main(["--probe"])

    if use_vtk:
        from opengate.visualization import main as vtk_main

        return vtk_main(
            [
                option
                for option in (
                    input,
                    "--backend",
                    backend,
                    *(["--slices", slices] if slices else []),
                    *(["--screenshot", screenshot] if screenshot else []),
                )
                if option
            ]
        )

    if not os.path.isfile(input):
        print("The file " + input + " does not exist")
        return ()

    if vrml and gdml:
        print("Choose between vrml or gdml")
        return ()

    if not vrml and not gdml:
        if "vrml" in input:
            vrml = True
        else:
            print("Choose either vrml or gdml")
            return ()

    if vrml:
        try:
            import pyvista
        except:
            print(
                "The module pyvista is not installed to be able to visualize vrml files. Execute:"
            )
            print("pip install pyvista")
            return
        pl = pyvista.Plotter()
        pl.import_vrml(input)  # self.simulation.visu_filename)
        pl.add_axes(line_width=5)
        pl.show()

    if gdml:
        try:
            import pyg4ometry
        except:
            print(
                "The module pyg4ometry is not installed to be able to visualize gdml files. Execute:"
            )
            print("pip install pyg4ometry")
            return
        r = pyg4ometry.gdml.Reader(input)  # self.simulation.visu_filename)
        l = r.getRegistry().getWorldVolume()
        v = pyg4ometry.visualisation.VtkViewerColouredMaterial()
        v.addLogicalVolume(l)
        v.view()


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
