from .ElementBase import *


class SourceBase(ElementBase):

    def __init__(self, name, g4_source):
        # type_name MUST be defined in class that inherit from SourceBase
        ElementBase.__init__(self, name)
        self.g4_source = g4_source
        # user info
        self.user_info.start_time = None
        self.user_info.end_time = None
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
        # for debug
        print('SourceBase destructor')

    def initialize(self, run_timing_intervals):
        ElementBase.initialize(self)
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.user_info.start_time:
            self.user_info.start_time = run_timing_intervals[0][0]
        if not self.user_info.end_time:
            self.user_info.end_time = run_timing_intervals[-1][1]
        # this will initialize and give user_info to the cpp side
        self.g4_source.initialize(self.user_info)

    def get_estimated_number_of_events(self, run_timing_interval):
        # FIXME see LATER
        exit()
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
        if run_timing_interval[0] <= self.user_info.start_time <= run_timing_interval[1]:
            return self.user_info.n
        return 0
