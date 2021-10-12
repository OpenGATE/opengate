import gam_gate as gam
import gam_g4 as g4
import uuid
import time


class TestActor(g4.GamVActor, gam.ActorBase):
    """
    Test actor: only py side (no cpp)
    For prototyping (slow)
    """

    type_name = 'TestActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        user_info.track_types_flag = False

    def __init__(self, user_info=None):
        # user_info can be null when create empty actor (that read file)
        if not user_info:
            user_info = gam.UserInfo('Actor', self.type_name, name=uuid.uuid4().__str__())
        gam.ActorBase.__init__(self, user_info)
        g4.GamVActor.__init__(self, user_info.__dict__)
        actions = {'StartSimulationAction', 'EndSimulationAction', 'BeginOfEventAction',
                   'EndOfRunAction', 'PreUserTrackingAction', 'SteppingAction'}
        self.AddActions(actions)
        # empty results for the moment
        self.run_count = 0
        self.event_count = 0
        self.track_count = 0
        self.step_count = 0
        self.duration = 0
        self.track_types = {}
        self.start_time = 0
        self.end_time = 0

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
        if not self:
            return ''
        s = f'Runs     {self.run_count}\n' \
            f'Events   {self.event_count}\n' \
            f'Tracks   {self.track_count}\n' \
            f'Step     {self.step_count}\n' \
            f'Duration {g4.G4BestUnit(self.duration, "Time")}\n' \
            f'PPS      {self.pps:.0f}\n' \
            f'TPS      {self.tps:.0f}\n' \
            f'SPS      {self.sps:.0f}'
        if self.user_info.track_types_flag:
            s += f'\n' \
                 f'Track types: {self.track_types}'
        return s

    def StartSimulationAction(self):
        self.start_time = time.time()

    def BeginOfEventAction(self, event):
        pass

    def PreUserTrackingAction(self, track):
        self.track_count += 1
        if self.user_info.track_types_flag:
            p = track.GetParticleName()
            try:
                self.track_types[p] += 1
            except:
                self.track_types[p] = 1

    def EndOfRunAction(self, run):
        self.run_count += 1
        self.event_count += run.GetNumberOfEvent()

    def SteppingAction(self, step, touchable):
        self.step_count += 1

    def EndSimulationAction(self):
        self.end_time = time.time()
        sec = gam.g4_units('s')
        self.duration = (self.end_time - self.start_time) * sec

    def write(self, filename):
        sec = gam.g4_units('s')
        f = open(filename, 'w+')
        s = f'# NumberOfRun    = {self.run_count}\n'
        s += f'# NumberOfEvents = {self.event_count}\n'
        s += f'# NumberOfTracks = {self.track_count}\n'
        s += f'# NumberOfSteps  = {self.step_count}\n'
        s += f'# NumberOfGeometricalSteps  = ?\n'
        s += f'# NumberOfPhysicalSteps     = ?\n'
        s += f'# ElapsedTime           = {self.duration / sec}\n'
        s += f'# ElapsedTimeWoInit     = {self.duration / sec}\n'
        s += f'# StartDate             = ?\n'
        s += f'# EndDate               = ?\n'
        s += f'# PPS (Primary per sec)      = {self.pps:.0f}\n'
        s += f'# TPS (Track per sec)        = {self.tps:.0f}\n'
        s += f'# SPS (Step per sec)         = {self.sps:.0f}\n'
        if self.user_info.track_types_flag:
            s += f'# Track types:\n'
            for t in self.track_types:
                s += f'# {t} = {self.track_types[t]}\n'
        f.write(s)
