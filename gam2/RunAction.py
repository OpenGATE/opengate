from box import Box

import gam  # needed for gam_setup
import geant4 as g4


class RunAction(g4.G4UserRunAction):
    """
    TODO
    """

    def __init__(self):
        g4.G4UserRunAction.__init__(self)
        print('RunAction constructor')
        self.BeginOfRunAction_actors = []
        self.EndOfRunAction_actors = []

    def register_actor(self, actor):
        print('run register', actor)
        actions = actor.g4_actor.actions
        if 'BeginOfRunAction' in actions:
            self.BeginOfRunAction_actors.append(actor.g4_actor)
        if 'EndOfRunAction' in actions:
            self.EndOfRunAction_actors.append(actor.g4_actor)
        print(self.EndOfRunAction_actors)

    def BeginOfrunAction(self, run):
        print('begin run')
        for actor in self.BeginOfRunAction_actors:
            actor.BeginOfRunAction(run)

    def EndOfRunAction(self, run):
        for actor in self.EndOfRunAction_actors:
            actor.ProcessBatch(True)
            actor.EndOfRunAction(run)
