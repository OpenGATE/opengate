import opengate as gate


def start_gdml_visu(filename):
    try:
        import pyg4ometry
    except Exception as exception:
        gate.warning(exception)
        gate.warning(
            "The module pyg4ometry is maybe not installed or is not working. Try: \n"
            "pip install pyg4ometry"
        )
        return
    r = pyg4ometry.gdml.Reader(filename)
    l = r.getRegistry().getWorldVolume()
    v = pyg4ometry.visualisation.VtkViewerColouredMaterial()
    v.addLogicalVolume(l)
    v.view()


def start_vrml_visu(filename):
    try:
        import pyvista
    except Exception as exception:
        gate.warning(exception)
        gate.warning(
            "The module pyvista is maybe not installed or is not working to be able to visualize vrml files. Try:\n"
            "pip install pyvista"
        )
        return
    pl = pyvista.Plotter()
    pl.import_vrml(filename)
    pl.set_background("black")
    pl.add_axes(line_width=5, color="white")
    pl.show()
