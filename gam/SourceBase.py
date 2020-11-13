from .ElementBase import *


class SourceBase(ElementBase):

    def __init__(self, name, g4_source):
        # type_name MUST be defined in class that inherit from SourceBase
        ElementBase.__init__(self, name)
        self.g4_source = g4_source
        # user info
        self.user_info.start_time = None
        self.user_info.end_time = None
        self.user_info.n = 0
        # needed variables to control the source
        self.shot_event_count = 0
        self.run_timing_intervals = False
        self.current_run_interval = None
        # g4 objects (shortcut for the one in source_manager)
        self.particle_table = None

    def __str__(self):
        s = f'{self.user_info.name}: {self.user_info}'
        return s

    def dump(self, level):
        # for the moment, level is ignored
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

    def initialize(self, run_timing_intervals):
        ElementBase.initialize(self)
        self.check_user_info()
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.user_info.start_time:
            self.user_info.start_time = run_timing_intervals[0][0]
        if not self.user_info.end_time:
            self.user_info.end_time = run_timing_intervals[-1][1]
        self.g4_source.initialize(self.user_info)

    def get_estimated_number_of_events(self, run_timing_interval):
        exit()
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
        if run_timing_interval[0] <= self.user_info.start_time <= run_timing_interval[1]:
            return self.user_info.n
        return 0

    def start_current_run(self, current_simulation_time, current_run_interval):
        exit()
        self.current_run_interval = current_run_interval
        # some source may need the current_simulation_time here

    def source_is_terminated(self, current_simulation_time):
        exit()
        # By default, the source if terminated if the time is
        # strictly larger than the end time
        if current_simulation_time > self.user_info.end_time:
            return True
        # if this is not the case, it can still be terminated
        # if a max number of event is reached
        if self.shot_event_count >= self.user_info.n:  # total_event_count:
            return True
        return False

    def get_next_event_info(self, time):
        exit()
        gam.fatal(f'SourceBase::get_next_event_info must be overloaded for source {self.user_info}')
        # must return next_time and next_event_id

    def generate_primaries(self, event, time):
        exit()
        gam.fatal(f'SourceBase::generate_primaries must be overloaded for source {self.user_info}')
