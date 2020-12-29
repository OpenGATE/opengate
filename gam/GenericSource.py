import gam
import gam_g4 as g4
from box import Box
from scipy.spatial.transform import Rotation


class GenericSource(gam.SourceBase):
    """
    FIXME. Not needed. DEBUG.
    """

    type_name = 'Generic'

    def __init__(self, name):
        gam.SourceBase.__init__(self, name)
        # initial user info
        self.user_info.particle = 'gamma'
        self.user_info.n = 0
        self.user_info.activity = 0
        # position
        self.user_info.position = Box()
        self.user_info.position.type = 'point'
        self.user_info.position.radius = 0
        self.user_info.position.size = [0, 0, 0]
        self.user_info.position.center = [0, 0, 0]
        self.user_info.position.rotation = Rotation.identity().as_matrix()
        # angle (direction)
        self.user_info.direction = Box()
        self.user_info.direction.type = 'iso'
        self.user_info.direction.momentum = [0, 0, 1]
        self.user_info.direction.focus_point = [0, 0, 0]
        # energy
        self.user_info.energy = Box()
        self.user_info.energy.type = 'mono'
        self.user_info.energy.mono = 0
        self.user_info.energy.sigma_gauss = 0

    def create_g4_source(self):
        self.g4_source = g4.GamGenericSource()
        return self.g4_source

    def initialize(self, run_timing_intervals):
        # Check user_info type
        if not isinstance(self.user_info, Box):
            gam.fatal(f'Generic Source: user_info must be a Box, but is: {self.user_info}')
        if not isinstance(self.user_info.position, Box):
            gam.fatal(f'Generic Source: user_info.position must be a Box, but is: {self.user_info.position}')
        if not isinstance(self.user_info.direction, Box):
            gam.fatal(f'Generic Source: user_info.direction must be a Box, but is: {self.user_info.direction}')
        if not isinstance(self.user_info.energy, Box):
            gam.fatal(f'Generic Source: user_info.energy must be a Box, but is: {self.user_info.energy}')
        # initialize
        gam.SourceBase.initialize(self, run_timing_intervals)
        if self.user_info.n > 0 and self.user_info.activity > 0:
            gam.fatal(f'Cannot use both n and activity, choose one: {self.user_info}')
        if self.user_info.n == 0 and self.user_info.activity == 0:
            gam.fatal(f'Choose either n or activity : {self.user_info}')
        if self.user_info.activity > 0:
            self.user_info.n = -1
        if self.user_info.n > 0:
            self.user_info.activity = -1
