import gam_g4 as g4


class RunAction(g4.G4UserRunAction):
    """
    User action at begin and end of run.
    Every time a run begin/end, the G4 engine call BeginOfRunAction and EndOfRunAction.
    The callback is then forwarded to all actors that need it.
    """

    def __init__(self):
        g4.G4UserRunAction.__init__(self)
        self.BeginOfRunAction_actors = []
        self.EndOfRunAction_actors = []

    def __del__(self):
        pass

    def register_actor(self, actor):
        actions = actor.actions
        if 'BeginOfRunAction' in actions:
            self.BeginOfRunAction_actors.append(actor)
        if 'EndOfRunAction' in actions:
            self.EndOfRunAction_actors.append(actor)

    def BeginOfRunAction(self, run):
        for actor in self.BeginOfRunAction_actors:
            actor.BeginOfRunAction(run)

    def EndOfRunAction(self, run):
        for actor in self.EndOfRunAction_actors:
            # actor.ProcessHitsPerBatch(True) # already done in GamVActor
            actor.EndOfRunAction(run)
