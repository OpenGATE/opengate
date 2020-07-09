import gam  # needed for gam_setup
import geant4 as g4
from box import Box


class SimulationStatisticsActor(g4.GateSimulationStatisticsActor):
    """
    TODO
    """

    def __init__(self):
        g4.GateSimulationStatisticsActor.__init__(self)
        print('SimulationStatistics::Constructor')
        self.run_count = 0
        self.event_count = 0
        self.track_count = 0
        self.track = Box()
        # self.step_count = 0
        self.batch_count = 0
        self.actions = ['BeginOfRunAction',
                        'EndOfRunAction',
                        'BeginOfEventAction',
                        'PreUserTrackingAction',
                        'ProcessHits']

    def __del__(self):
        print('SimulationStatistics python destructor')
        # del self.g4_runManager

    def __str__(self):
        s = f'Runs:     {self.run_count}\n' \
            f'Events:   {self.event_count}\n' \
            f'Tracks:   {self.track_count}\n' \
            f'Batch;    {self.batch_count}\n' \
            f'Step:     {self.step_count}\n' \
            f'Particles {self.track}'
        return s

    def BeginOfRunAction(self, run):
        self.run_count += 1

    def BeginOfEventAction(self, event):
        self.event_count += 1

    def PreUserTrackingAction(self, track):
        #p = track.GetParticleDefinition()
        #n = p.GetParticleName() # GetPDGEncoding
        #if n not in self.track:
        #    self.track[n] = 0
        #self.track[n] += 1
        self.track_count += 1

    def StepBatchAction(self):
        print('step batch', self.batch_count, self.step_count, self.batch_size, self.batch_step_count)
        self.batch_count += 1
        # elf.step_count += self.GetStepCountInBatch()
