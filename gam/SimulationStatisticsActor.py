import gam
import gam_g4 as g4
from box import Box
import time


class SimulationStatisticsActor(g4.GamVActor, gam.ActorBase):
    """
    TODO
    """

    type_name = 'SimulationStatisticsActor'

    def __init__(self, name):
        g4.GamVActor.__init__(self, self.type_name)
        gam.ActorBase.__init__(self, name)
        # default actions
        self.actions = [
            'BeginOfRunAction',
            'EndOfRunAction',
            'BeginOfEventAction',
            'PreUserTrackingAction',
            'ProcessHits']
        self.run_count = 0
        self.event_count = 0
        self.track_count = 0
        self.step_count = 0
        self.track = Box()  # FIXME not used yet. Maybe later
        # self.step_count = 0
        self.batch_count = 0
        self.batch_size = 50000
        self.duration = 0
        self.start_time = 0
        self.stop_time = 0

    def __del__(self):
        pass

    @property
    def pps(self):
        sec = gam.g4_units('s')
        if self.duration != 0:
            return self.event_count / self.duration * sec
        return 0

    @property
    def tps(self):
        sec = gam.g4_units('s')
        if self.duration != 0:
            return self.track_count / self.duration * sec
        return 0

    @property
    def sps(self):
        sec = gam.g4_units('s')
        if self.duration != 0:
            return self.step_count / self.duration * sec
        return 0

    def __str__(self):
        s = f'Runs     {self.run_count}\n' \
            f'Events   {self.event_count}\n' \
            f'Tracks   {self.track_count}\n' \
            f'Step     {self.step_count}\n' \
            f'Batch    {self.batch_count}\n' \
            f'Duration {g4.G4BestUnit(self.duration, "Time")}\n' \
            f'PPS      {self.pps:.0f}\n' \
            f'TPS      {self.tps:.0f}\n' \
            f'SPS      {self.sps:.0f}'
        return s

    def BeginOfRunAction(self, run):
        self.start_time = time.time()
        self.run_count += 1

    def EndOfRunAction(self, run):
        self.stop_time = time.time()
        sec = gam.g4_units('s')
        self.duration = (self.stop_time - self.start_time) * sec
        # g4.GamSimulationStatisticsActor.EndOfRunAction(self, run)
        g4.GamVActor.EndOfRunAction(self, run)

    def BeginOfEventAction(self, event):
        self.event_count += 1

    def PreUserTrackingAction(self, track):
        # p = track.GetParticleDefinition()
        # n = p.GetParticleName() # GetPDGEncoding
        # if n not in self.track:
        #    self.track[n] = 0
        # self.track[n] += 1
        self.track_count += 1

    def SteppingBatchAction(self):
        # print('StatActor process batch', self.batch_count,
        #      self.step_count, self.batch_size, self.batch_step_count)
        self.batch_count += 1
        self.step_count += self.batch_step_count
