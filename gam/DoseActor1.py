import gam_g4 as g4


class DoseActor1(g4.GamVActorWithSteppingAction):
    """
    TODO
    """

    def __init__(self, actor_info):
        g4.GamVActorWithSteppingAction.__init__(self, 'DoseActor')
        self.user_info = actor_info
        self.actions = ['ProcessHits']
        self.debug = 0
        self.debug_hits_count = 0

    def __str__(self):
        s = f'Dose Actor1 TODO {self.debug} {self.debug_hits_count}'
        return s

    def SteppingAction(self, step, theTouchable):
        # print('DoseActor stepping action')
        preGlobal = step.GetPreStepPoint().GetPosition()  # very slow !!??
        touchable = step.GetPreStepPoint().GetTouchable()
        depth = touchable.GetHistoryDepth()
        preLocal = touchable.GetHistory().GetTransform(depth).TransformPoint(preGlobal)
        # print(f'Position depth={depth} {touchable.GetVolume(0).GetName()} {preGlobal}     {preLocal}')
        self.debug += preLocal.x
        self.debug_hits_count += 1
