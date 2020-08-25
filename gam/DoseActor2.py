import gam_g4 as g4
import itk


class DoseActor2(g4.GamDoseActor2):
    """
    TODO
    """

    def __init__(self):
        g4.GamDoseActor2.__init__(self)
        self.actions = ['EndOfRunAction',  # Needed to process the remaining last batch
                        'ProcessHits']
        self.debug = 0
        self.batch_size = 10000
        self.debug_hits_count = 0
        self.debug_batch_count = 0

    def __str__(self):
        s = f'Dose Actor2 TODO {self.debug} {self.debug_hits_count} batch={self.debug_batch_count}'
        return s

    def SteppingBatchAction(self):
        # print('Dose2 actor batch ', self.batch_step_count)
        positions = self.vpositions[:self.batch_step_count]  # cost time ! dont know why
        # print('DoseActor2 stepping action Batch', self.batch_step_count, len(positions))
        self.debug += sum(p.x for p in positions)
        self.debug_hits_count += self.batch_step_count
        # preGlobal = step.GetPreStepPoint().GetPosition()
        # touchable = step.GetPreStepPoint().GetTouchable()
        # depth = touchable.GetHistoryDepth()
        # preLocal = touchable.GetHistory().GetTransform(depth).TransformPoint(preGlobal)
        # print(f'Position depth={depth} {touchable.GetVolume(0).GetName()} {preGlobal}     {preLocal}')
        self.debug_batch_count += 1
