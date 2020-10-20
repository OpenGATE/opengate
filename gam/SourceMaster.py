import gam_g4 as g4


class SourceMaster(g4.G4VUserPrimaryGeneratorAction):
    """
    Implement G4VUserPrimaryGeneratorAction.
    The function GeneratePrimaries will be called by Geant4 engine.
    This class is required because G4VUserPrimaryGeneratorAction can only be created after
    the Physic List
    """

    def __init__(self, source_manager):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        self.source_manager = source_manager

    def GeneratePrimaries(self, event):
        # Override G4VUserPrimaryGeneratorAction::GeneratePrimaries
        self.source_manager.generate_primaries(event)
