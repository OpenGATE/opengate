import gam_g4 as g4


class EventActionOLD(g4.G4UserEventAction):
    """
    TODO
    """

    def __init__(self):
        g4.G4UserEventAction.__init__(self)
        self.BeginOfEventAction_actors = []
        self.EndOfEventAction_actors = []

    def register_actor(self, actor):
        actions = actor.actions
        if 'BeginOfEventAction' in actions:
            self.BeginOfEventAction_actors.append(actor)
        if 'EndOfEventAction' in actions:
            self.EndOfEventAction_actors.append(actor)

    def BeginOfEventAction(self, event):
        for actor in self.BeginOfEventAction_actors:
            actor.BeginOfEventAction(event)

    def EndOfEventAction(self, event):
        for actor in self.EndOfEventAction_actors:
            actor.EndOfEventAction(event)
