from box import Box

import gam  # needed for gam_setup
import geant4 as g4

class BActor(g4.GateVActor):
    """
    TODO
    """

    def __init__(self):
        g4.GateVActor.__init__(self, "BActor")
        print('BActor::Constructor')
        self.nb_event = 0
        self.nb_step = 0

    def __del__(self):
        print('BActor destructor')

    def BeginOfEventAction(self, event):
        # print('BActor : BeginOfEventAction', event)
        self.nb_event += 1

    def SteppingAction(self, step):
        # print('BActor : SteppingAction', step)
        self.nb_step += 1

