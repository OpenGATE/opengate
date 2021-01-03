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

    def __del__(self):
        print('GamSimulationStatisticsActor destructor')

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

    def __str__(self):
        s = f'Runs     {self.GetRunCount()}\n' \
            f'Events   {self.GetEventCount()}\n' \
            f'Tracks   {self.GetTrackCount()}\n' \
            f'Step     {self.GetStepCount()}\n' \
            f'fDuration {g4.G4BestUnit(self.fDuration, "Time")}\n' \
            f'PPS      {self.pps:.0f}\n' \
            f'TPS      {self.tps:.0f}\n' \
            f'SPS      {self.sps:.0f}'
        return s
