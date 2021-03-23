from ..UserElement import *
from gam.VolumeManager import __world_name__


class SourceBase(UserElement):
    """
        Base class for all source types.
    """

    @staticmethod
    def set_default_user_info(user_info):
        gam.UserElement.set_default_user_info(user_info)
        user_info.mother = __world_name__
        user_info.start_time = None
        user_info.end_time = None

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from SourceBase
        super().__init__(user_info)
        # the cpp counterpart of the source
        self.g4_source = None
        # all times intervals
        self.run_timing_intervals = None

    def __str__(self):
        s = f'{self.user_info.name}: {self.user_info}'
        return s

    def dump(self, level):
        # for the moment, level is ignored
        r = [self.user_info.start_time, self.user_info.end_time]
        sec = gam.g4_units('s')
        start = 'no start time'
        end = 'no end time'
        if self.user_info.start_time is not None:
            start = f'{self.user_info.start_time / sec} sec'
        if self.user_info.end_time is not None:
            end = f'{self.user_info.end_time / sec} sec'
        s = f'Source name        : {self.user_info.name}\n' \
            f'Source type        : {self.user_info.type}\n' \
            f'Start time         : {start}\n' \
            f'End time           : {end}'
        # f'N events           : {self.user_info.n}\n' \
        # f'Generated events   : {self.shot_event_count}\n' \
        # FIXME f'Estim. total events: {self.get_estimated_number_of_events(r):.0f}'
        return s

    def __del__(self):
        pass

    def create_g4_source(self):
        gam.fatal('The function "create_g4_source" *must* be overridden')

    def pre_initialize(self):
        """
        This method can be overwritten to perform tasks before the cpp initialization.
        For example for checking user parameters.
        """
        pass

    def initialize(self, run_timing_intervals):
        print('sourceBase', run_timing_intervals)
        UserElement.initialize(self)
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.user_info.start_time:
            self.user_info.start_time = run_timing_intervals[0][0]
        if not self.user_info.end_time:
            self.user_info.end_time = run_timing_intervals[-1][1]
        # this will initialize and give user_info to the cpp side
        print('befire InitializeUserInfo', self.user_info)
        self.g4_source.InitializeUserInfo(self.user_info)

    def get_estimated_number_of_events(self, run_timing_interval):
        # FIXME see LATER
        exit()
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
        if run_timing_interval[0] <= self.user_info.start_time <= run_timing_interval[1]:
            return self.user_info.n
        return 0
