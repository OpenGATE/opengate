from box import Box

import gam  # needed for gam_setup
import geant4 as g4


class Action(g4.G4VUserActionInitialization):
    """
    TODO
    """

    def __init__(self, source, actors):
        """
        TODO
        """
        print('Action:: Constructor')
        g4.G4VUserActionInitialization.__init__(self)
        self.g4_source = source
        self.g4_actors = actors

    def __del__(self):
        print('Action destructor')

    def BuildForMaster(self):
        print('Action::BuildForMaster')
        # self.runAction = B1RunAction()
        # self.SetUserAction(self.runAction)

    def Build(self):
        print('Action::Build')
        self.SetUserAction(self.g4_source)
        #
        # self.runAction = B1RunAction()
        # self.SetUserAction(self.runAction)

        # self.eventAction = B1EventAction()  # self.runAction)
        # self.SetUserAction(self.g4_actors.GetEventActions())

        # # self.stepAction = B1SteppingAction()
        # self.stepAction = B1SteppingBatchAction()
        # self.SetUserAction(self.g4_actors.gate_user_stepping_action)
