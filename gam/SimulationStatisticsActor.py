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
            f'Duration {g4.G4BestUnit(self.duration, "Time")}\n' \
            f'PPS      {self.pps:.0f}\n' \
            f'TPS      {self.tps:.0f}\n' \
            f'SPS      {self.sps:.0f}'
        return s
