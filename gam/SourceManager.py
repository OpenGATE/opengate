from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class SourceManager(g4.G4VUserPrimaryGeneratorAction):
    """
    Implement G4VUserPrimaryGeneratorAction.
    The function GeneratePrimaries will be called by Geant4 engine.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    def __init__(self):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        self.simu_time = 0
        self.current_source = False

    def __del__(self):
        print(f'destructor Source manager')

    def prepare_generate_primaries(self, simu_time, source):
        self.simu_time = simu_time
        self.current_source = source

    def GeneratePrimaries(self, event):
        self.current_source.GeneratePrimaries(event, self.simu_time)
