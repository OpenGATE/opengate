from .ElementBase import *


class SourceBase(ElementBase):

    def __init__(self, name):
        # source_type MUST be declared in class that inherit from SourceBase
        ElementBase.__init__(self, self.source_type, name)
        # user info
        self.user_info.start_time = None
        self.user_info.end_time = None
        self.user_info.n = None
        # needed variables to control the source
        self.current_time = 0.0
        self.shot_event_count = 0
        self.total_event_count = gam.SourceManager.max_int
        self.run_timing_intervals = False
        self.current_run_interval = None

    def __str__(self):
        r = [self.user_info.start_time, self.user_info.end_time]
        sec = gam.g4_units('s')
        start = 'no start time'
        end = 'no end time'
        if self.user_info.start_time:
            start = f'{self.user_info.start_time / sec} sec'
        if self.user_info.end_time:
            end = f'{self.user_info.end_time / sec} sec'
        s = f'Source name        : {self.user_info.name}\n' \
            f'Source type        : {self.user_info.type}\n' \
            f'Start time         : {start}\n' \
            f'End time           : {end}\n' \
            f'N events           : {self.user_info.n}\n' \
            f'Generated events   : {self.shot_event_count}\n' \
            f'Estim. total events: {self.get_estimated_number_of_events(r):.0f}'
        return s

    def __del__(self):
        # for debug
        print('SourceBase destructor')

    def set_current_run_interval(self, current_run_interval):
        self.current_run_interval = current_run_interval

    def initialize(self, run_timing_intervals):
        self.check_user_info()
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.user_info.start_time:
            self.user_info.start_time = run_timing_intervals[0][0]
        if not self.user_info.end_time:
            self.user_info.end_time = run_timing_intervals[-1][1]
        if self.user_info.n:
            self.total_event_count = self.user_info.n

    def get_estimated_number_of_events(self, run_timing_interval):
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
        if run_timing_interval[0]:
            if run_timing_interval[0] <= self.user_info.start_time <= run_timing_interval[1]:
                return self.total_event_count
        return 0

    def prepare_for_next_run(self, sim_time, current_run_interval):
        # some sources may need this function
        pass

    def source_is_terminated(self, sim_time):
        # By default, the source if terminated if the time is
        # strictly larger than the end time
        if sim_time > self.user_info.end_time:
            return True
        # if this is not the case, it can still be terminated
        # if a max number of event is reached
        if self.shot_event_count >= self.total_event_count:
            return True
        return False

    def get_next_event_info(self, time):
        gam.fatal(f'SourceBase::get_next_event_info must be overloaded for source {self.user_info}')
        # return 0, 0 ## return next_time and next_event_id

    def generate_primaries(self, event, time):
        gam.fatal(f'SourceBase::generate_primaries must be overloaded for source {self.user_info}')
