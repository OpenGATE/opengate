import gam
import gam_g4 as g4


class Test1Source(gam.SourceBase):
    """
    FIXME. Not needed. DEBUG.
    """

    type_name = 'Test1'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name, g4.GamTest1Source())
        # initial user info
        self.user_info.particle = 'gamma'
        self.user_info.energy = 0
        self.user_info.diameter = 0
        self.user_info.translation = [0, 0, 0]
        self.user_info.n = 0
        self.user_info.activity = 0

    def initialize(self, run_timing_intervals):
        gam.SourceBase.initialize(self, run_timing_intervals)
        if self.user_info.n > 0 and self.user_info.activity > 0:
            gam.fatal(f'Cannot use both n and activity, choose one: {self.user_info}')
        if self.user_info.n == 0 and self.user_info.activity == 0:
            gam.fatal(f'Choose either n or activity : {self.user_info}')
        if self.user_info.activity > 0:
            self.user_info.n = -1
        if self.user_info.n > 0:
            self.user_info.activity = -1
