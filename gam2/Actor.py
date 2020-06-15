from box import Box

import gam  # needed for gam_setup
import geant4 as g4

class Actor:
    """
    TODO
    """

    def __init__(self, actors):
        """
        TODO
        """
        print('Actor:: Constructor')
        self.actors = actors

        # Later -> param from 'actors' to GateSteppingAction
        self.gate_user_stepping_action = g4.GateUserSteppingAction()

        # later other run event track

    def __del__(self):
        print('Actor destructor')
