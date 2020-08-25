from box import Box

import gam  # needed for gam_setup
import gam_g4 as g4


class TestProtonCppSource(gam.SourceBase):
    """
    FIXME. Not needed. DEBUG.
    """

    def __init__(self, source_info):
        """
        TODO
        """
        # g4.GamTestProtonSource.__init__(self)
        gam.SourceBase.__init__(self, source_info)
        self.g4_source = g4.GamTestProtonSource()

    def get_next_event_info(self, current_time):
        # this source does not manage the time, only the nb of particle
        # so whatever the current_time, we consider 0
        return 0, self.shot_event_count + 1

    def GeneratePrimaries(self, event, sim_time):
        # print('Generate pr', event, sim_time)
        self.g4_source.GeneratePrimaries(event)
        self.shot_event_count += 1
