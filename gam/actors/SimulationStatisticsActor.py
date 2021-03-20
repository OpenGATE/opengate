import gam
import gam_g4 as g4


class SimulationStatisticsActor(g4.GamSimulationStatisticsActor, gam.ActorBase):
    """
    TODO
    """

    type_name = 'SimulationStatisticsActor'

    def __init__(self, name):
        g4.GamSimulationStatisticsActor.__init__(self, self.type_name)
        gam.ActorBase.__init__(self, name)
        # default user options
        self.user_info.track_types_flag = False

    def __del__(self):
        pass

    def initialize(self):
        self.check_user_info()
        self.track_types_flag = self.user_info.track_types_flag

    @property
    def pps(self):
        sec = gam.g4_units('s')
        if self.fDuration != 0:
            return self.GetEventCount() / self.fDuration * sec
        return 0

    @property
    def tps(self):
        sec = gam.g4_units('s')
        if self.fDuration != 0:
            return self.GetTrackCount() / self.fDuration * sec
        return 0

    @property
    def sps(self):
        sec = gam.g4_units('s')
        if self.fDuration != 0:
            return self.GetStepCount() / self.fDuration * sec
        return 0

    @property
    def track_types(self):
        # (it depends if read from disk or computed)
        if self.GetTrackTypes() != {}:
            return self.GetTrackTypes()
        return self.fTrackTypes

    @property
    def track_types_flag(self):
        return self.fTrackTypesFlag

    @track_types_flag.setter
    def track_types_flag(self, value):
        self.SetTrackTypesFlag(value)

    def __str__(self):
        s = f'Runs     {self.GetRunCount()}\n' \
            f'Events   {self.GetEventCount()}\n' \
            f'Tracks   {self.GetTrackCount()}\n' \
            f'Step     {self.GetStepCount()}\n' \
            f'Duration {g4.G4BestUnit(self.fDuration, "Time")}\n' \
            f'PPS      {self.pps:.0f}\n' \
            f'TPS      {self.tps:.0f}\n' \
            f'SPS      {self.sps:.0f}'
        if self.track_types_flag:
            s += f'\n' \
                 f'Track types: {self.track_types}'
        return s

    def write(self, filename):
        sec = gam.g4_units('s')
        f = open(filename, 'w+')
        s = f'# NumberOfRun    = {self.GetRunCount()}\n'
        s += f'# NumberOfEvents = {self.GetEventCount()}\n'
        s += f'# NumberOfTracks = {self.GetTrackCount()}\n'
        s += f'# NumberOfSteps  = {self.GetStepCount()}\n'
        s += f'# NumberOfGeometricalSteps  = ?\n'
        s += f'# NumberOfPhysicalSteps     = ?\n'
        s += f'# ElapsedTime           = {self.fDuration / sec}\n'
        s += f'# ElapsedTimeWoInit     = {self.fDuration / sec}\n'
        s += f'# StartDate             = ?\n'
        s += f'# EndDate               = ?\n'
        s += f'# PPS (Primary per sec)      = {self.pps:.0f}\n'
        s += f'# TPS (Track per sec)        = {self.tps:.0f}\n'
        s += f'# SPS (Step per sec)         = {self.sps:.0f}\n'
        if self.track_types_flag:
            s += f'# Track types:\n'
            for t in self.track_types:
                s += f'# {t} = {self.track_types[t]}\n'
        f.write(s)
