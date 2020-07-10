from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class TrackingAction(g4.G4UserTrackingAction):
    """
    TODO
    """

    def __init__(self):
        g4.G4UserTrackingAction.__init__(self)
        print('TrackingAction constructor')
        self.PreUserTrackingAction_actors = []
        self.PostUserTrackingAction_actors = []

    def register_actor(self, actor):
        actions = actor.g4_actor.actions
        if 'PreUserTrackingAction' in actions:
            self.PreUserTrackingAction_actors.append(actor.g4_actor)
        if 'PostUserTrackingAction' in actions:
            self.PostUserTrackingAction_actors.append(actor.g4_actor)

    def PreUserTrackingAction(self, track):
        for actor in self.PreUserTrackingAction_actors:
            actor.PreUserTrackingAction(track)

    def PostUserTrackingAction(self, track):
        for actor in self.PostUserTrackingAction_actors:
            actor.PostUserTrackingAction(track)
