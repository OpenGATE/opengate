import gam  # needed for gam_setup
import gam_g4 as g4


class ActionManager(g4.G4VUserActionInitialization):
    """
    TODO
    """

    def __init__(self, source):
        g4.G4VUserActionInitialization.__init__(self)
        #self.g4_PrimaryGenerator = source
        self.g4_PrimaryGenerator = []
        self.g4_main_PrimaryGenerator = None
        self.source_manager = source
        self.g4_RunAction = None
        self.g4_EventAction = None
        self.g4_TrackingAction = None

    def __del__(self):
        pass

    def BuildForMaster(self):
        # function call only in MT mode, for the master thread
        self.g4_main_PrimaryGenerator = self.source_manager.build()
        # set the actions for Run
        # self.g4_RunAction = gam.RunAction()
        # self.SetUserAction(self.g4_RunAction)

    def Build(self):
        gam.warning('ActionManager Build')

        # when no MT
        if not self.g4_main_PrimaryGenerator:
            self.g4_main_PrimaryGenerator = self.source_manager.build()

        # set the source first
        # FIXME
        p = self.source_manager.create_master_source()
        self.SetUserAction(p)
        self.g4_PrimaryGenerator.append(p)

        # FIXME
        # set the actions for Run
        #self.g4_RunAction = gam.RunAction()
        #self.SetUserAction(self.g4_RunAction)
        # set the actions for Event
        # self.g4_EventAction = gam.EventAction()
        #self.g4_EventAction = g4.GamEventAction()
        #self.SetUserAction(self.g4_EventAction)
        # set the actions for Track
        # self.g4_TrackingAction = gam.TrackingAction()
        #self.g4_TrackingAction = g4.GamTrackingAction()
        #self.SetUserAction(self.g4_TrackingAction)
