#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import os


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--input", "-i", default="", help="Input visualization file")
@click.option("--vrml", "-v", is_flag=True, help="VRML file")
@click.option("--gdml", "-g", is_flag=True, help="GDML file")
def go(input, vrml, gdml):
    if not os.path.isfile(input):
        print("The file " + input + " does not exist")
        return ()

    if vrml and gdml:
        print("Choose between vrml or gdml")
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
