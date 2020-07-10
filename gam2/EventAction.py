from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class EventAction(g4.G4UserEventAction):
    """
    TODO
    """

    def __init__(self):
        g4.G4UserEventAction.__init__(self)
        print('EventAction constructor')
        self.BeginOfEventAction_actors = []
        self.EndOfEventAction_actors = []

    def register_actor(self, actor):
        actions = actor.g4_actor.actions
        if 'BeginOfEventAction' in actions:
            self.BeginOfEventAction_actors.append(actor.g4_actor)
        if 'EndOfEventAction' in actions:
            self.EndOfEventAction_actors.append(actor.g4_actor)

    def BeginOfEventAction(self, event):
        for actor in self.BeginOfEventAction_actors:
            actor.BeginOfEventAction(event)

    def EnOfEventAction(self, event):
        for actor in self.EnOfEventAction_actors:
            actor.EnOfEventAction(event)
