import os
from .helpers import fatal, warning
from opengate import EngineBase
from opengate_core import GateInfo, G4VisExecutive
from .helpers_visu import start_gdml_visu, start_vrml_visu


class VisualisationEngine(EngineBase):
    """
    Main class to manage visualisation
    """

    def __init__(self, simulation_engine):
        self.g4_vis_executive = None
        self.current_visu_filename = None
        self._is_closed = None
        self.simulation_engine = simulation_engine
        self.simulation = simulation_engine.simulation
        EngineBase.__init__(self, self)

    def __del__(self):
        if self.simulation_engine.verbose_destructor:
            warning("Deleting VisualisationEngine")

    def close(self):
        if self.simulation_engine.verbose_close:
            warning(f"Closing VisualisationEngine is_closed = {self._is_closed}")
        self._is_closed = True

    def release_g4_references(self):
        self.g4_vis_executive = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def initialize_visualisation(self):
        ui = self.simulation.user_info
        if not ui.visu:
            return

        # check if filename is set when needed
        if "only" in ui.visu_type and ui.visu_filename is None:
            fatal(f'You must define a visu_filename with "{ui.visu_type}" is set')

        # set the current filename (maybe changed is no visu_filename)
        self.current_visu_filename = ui.visu_filename

        # gdml
        if ui.visu_type == "gdml" or ui.visu_type == "gdml_file_only":
            self.initialize_visualisation_gdml()

        # vrml
        if ui.visu_type == "vrml" or ui.visu_type == "vrml_file_only":
            self.initialize_visualisation_vrml()

        # G4 stuff
        self.g4_vis_executive = G4VisExecutive("all")
        self.g4_vis_executive.Initialize()

    def initialize_visualisation_gdml(self):
        ui = self.simulation.user_info
        # Check when GDML is activated, if G4 was compiled with GDML
        gi = GateInfo
        if not gi.get_G4GDML():
            warning(
                "Visualization with GDML not available in Geant4. Check G4 compilation."
            )
        if self.current_visu_filename is None:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.gdml"

    def initialize_visualisation_vrml(self):
        ui = self.simulation.user_info
        if ui.visu_filename is not None:
            os.environ["G4VRMLFILE_FILE_NAME"] = ui.visu_filename
        else:
            self.current_visu_filename = f"gate_visu_{os.getpid()}.wrl"
            os.environ["G4VRMLFILE_FILE_NAME"] = self.current_visu_filename

    def start_visualisation(self):
        ui = self.simulation.user_info
        if not ui.visu:
            return

        # VRML ?
        if ui.visu_type == "vrml":
            start_vrml_visu(self.current_visu_filename)

        # GDML ?
        if ui.visu_type == "gdml":
            start_gdml_visu(self.current_visu_filename)

        # remove the temporary file
        if ui.visu_filename is None:
            try:
                os.remove(self.current_visu_filename)
            except:
                pass
