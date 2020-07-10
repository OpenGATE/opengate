from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4
#import itk


class DoseActor(g4.GateDoseActor):
    # class DoseActor(g4.GateVActor):
    """
    TODO
    """

    def __init__(self):
        # g4.GateVActor.__init__(self, 'toto')
        g4.GateDoseActor.__init__(self)
        print('DoseActor::Constructor')
        self.nb_event = 0
        self.nb_step = 0
        self.nb_batch = 0
        self.edep = 0
        self.edep2 = 0
        self.actions = ['BeginOfRunAction',
                        'BeginOfEventAction',
                        'BeginOfTrackAction',
                        'ProcessHits']

    def __del__(self):
        print('DoseActor python destructor')
        #del self.g4_runManager

    def print_debug(self):
        self.nb_step = self.GetNbStep()
        print('BActor final results',
              self.nb_event, self.nb_step, self.nb_batch, self.edep, self.edep2)

    def BeginOfEventAction(self, event):
        # print('BActor : BeginOfEventAction', event)
        self.nb_event += 1

    def SteppingBatchAction(self):
        print('py actor batch', self.nb_batch)
        self.nb_batch += 1
        #for s in self.steps:
        #    self.edep += s.GetTotalEnergyDeposit()
        #print(type(self.steps))
        #for s in self.step_edep:
        #    self.edep += s
        self.edep2 += sum(self.step_edep)
        max = 0
        min = 100000
        for p in self.step_position:
            if p[2]> max:
                max = p[2]
            if p[2] < min:
                min = p[2]
        print(min, max)