from box import Box

import gam  # needed for gam_setup
import geant4 as g4
import gam2


class Actions(g4.G4VUserActionInitialization):
    """
    TODO
    """

    def __init__(self, source):
        """
        TODO
        """
        print('Actions::Constructor')
        g4.G4VUserActionInitialization.__init__(self)
        self.g4_source = source
        self.g4_run_action = None
        self.g4_event_action = None
        self.g4_tracking_action = None

    def __del__(self):
        print('Actions destructor')

    def BuildForMaster(self):
        print('Action::BuildForMaster')
        print('should not be there for the moment (maybe later for multi thread)')
        exit(0)

    def Build(self):
        print('Action::Build')
        # set the source first
        self.SetUserAction(self.g4_source)
        # set the actions for Run
        self.g4_run_action = gam2.RunAction()
        self.SetUserAction(self.g4_run_action)
        # set the actions for Event
        self.g4_event_action = gam2.EventAction()
        self.SetUserAction(self.g4_event_action)
        # set the actions for Track
        self.g4_tracking_action = gam2.TrackingAction()
        self.SetUserAction(self.g4_tracking_action)
