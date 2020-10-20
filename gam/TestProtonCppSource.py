import gam
import gam_g4 as g4


class TestProtonCppSource(gam.SourceBase):
    """
    FIXME. Not needed. DEBUG.
    """

    source_type = 'TestProtonCpp'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        self.user_info.n = 1
        self.g4_source = None

    def get_next_event_info(self, current_time):
        # this source does not manage the time, only the nb of particle
        # so whatever the current_time, we consider 0
        return 0, self.shot_event_count + 1

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)
        self.g4_source = g4.GamTestProtonSource()

    def generate_primaries(self, event, sim_time):
        # print('Generate pr', event, sim_time)
        self.g4_source.GeneratePrimaries(event)
        self.shot_event_count += 1
