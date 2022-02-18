import gam_gate as gam
import gam_g4 as g4
import uuid
from box import Box


class SimulationStatisticsActor(g4.GamSimulationStatisticsActor, gam.ActorBase):
    """
    Store statistics about a simulation run.
    """

    type_name = 'SimulationStatisticsActor'

    @staticmethod
    def set_default_user_info(user_info):
        gam.ActorBase.set_default_user_info(user_info)
        user_info.track_types_flag = False
        user_info.output = ''

    def __init__(self, user_info=None):
        # user_info can be null when create empty actor (that read file)
        if not user_info:
            user_info = gam.UserInfo('Actor', self.type_name, name=uuid.uuid4().__str__())
        gam.ActorBase.__init__(self, user_info)
        g4.GamSimulationStatisticsActor.__init__(self, user_info.__dict__)
        actions = {'EndSimulationAction'}
        self.AddActions(actions)
        # actions are also set from the cpp side
        # empty results for the moment
        self.counts = Box()
        self.counts.run_count = 0
        self.counts.event_count = 0
        self.counts.track_count = 0
        self.counts.step_count = 0
        self.counts.duration = 0
        self.counts.start_time = 0
        self.counts.stop_time = 0
        self.counts.init = 0
        self.counts.track_types = {}

    def __del__(self):
        pass

    @property
    def pps(self):
        sec = gam.g4_units('s')
        if self.counts.duration != 0:
            return self.counts.event_count / self.counts.duration * sec
        return 0

    @property
    def tps(self):
        sec = gam.g4_units('s')
        if self.counts.duration != 0:
            return self.counts.track_count / self.counts.duration * sec
        return 0

    @property
    def sps(self):
        sec = gam.g4_units('s')
        if self.counts.duration != 0:
            return self.counts.step_count / self.counts.duration * sec
        return 0

    def __str__(self):
        if not self.counts:
            return ''
        sec = gam.g4_units('second')
        s = f'Runs      {self.counts.run_count}\n' \
            f'Events    {self.counts.event_count}\n' \
            f'Tracks    {self.counts.track_count}\n' \
            f'Step      {self.counts.step_count}\n' \
            f'Init      {self.counts.init/sec} \t{g4.G4BestUnit(self.counts.init, "Time")}\n' \
            f'Duration  {self.counts.duration/sec} \t{g4.G4BestUnit(self.counts.duration, "Time")}\n' \
            f'PPS       {self.pps:.0f}\n' \
            f'TPS       {self.tps:.0f}\n' \
            f'SPS       {self.sps:.0f}\n' \
            f'start     {self.counts.start_time}\n' \
            f'stop      {self.counts.stop_time}'
        if self.user_info.track_types_flag:
            s += f'\n' \
                 f'Track types: {self.counts.track_types}'
        return s

    def EndSimulationAction(self):
        g4.GamSimulationStatisticsActor.EndSimulationAction(self)
        self.counts = Box(self.GetCounts())
        # write the file if an output filename was set
        if self.user_info.output != '':
            self.write(self.user_info.output)

    """
        It is feasible to get callback every Run, Event, Track, Step in the python side. 
        However, it is VERY time consuming. For SteppingAction, expect large performance drop. 
        It could be however useful for prototyping or tests.
        
        it requires "trampoline functions" on the cpp side.   
        
        # feasible but very slow ! 
        def SteppingAction(self, step, touchable):
            g4.GamSimulationStatisticsActor.SteppingAction(self, step, touchable)
            do_something()
    """

    def write(self, filename):
        sec = gam.g4_units('s')
        f = open(filename, 'w+')
        s = f'# NumberOfRun    = {self.counts.run_count}\n'
        s += f'# NumberOfEvents = {self.counts.event_count}\n'
        s += f'# NumberOfTracks = {self.counts.track_count}\n'
        s += f'# NumberOfSteps  = {self.counts.step_count}\n'
        s += f'# NumberOfGeometricalSteps  = ?\n'
        s += f'# NumberOfPhysicalSteps     = ?\n'
        s += f'# ElapsedTime           = {self.counts.duration / sec + self.counts.init / sec}\n'
        s += f'# ElapsedTimeWoInit     = {self.counts.duration / sec}\n'
        s += f'# StartDate             = ?\n'
        s += f'# EndDate               = ?\n'
        s += f'# PPS (Primary per sec)      = {self.pps:.0f}\n'
        s += f'# TPS (Track per sec)        = {self.tps:.0f}\n'
        s += f'# SPS (Step per sec)         = {self.sps:.0f}\n'
        if self.user_info.track_types_flag:
            s += f'# Track types:\n'
            for t in self.counts.track_types:
                s += f'# {t} = {self.counts.track_types[t]}\n'
        f.write(s)
