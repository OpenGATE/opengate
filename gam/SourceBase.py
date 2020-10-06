import gam
import gam_g4 as g4


class SourceBase(g4.G4VUserPrimaryGeneratorAction):

    def __init__(self, source_info):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        self.Bq = gam.g4_units('Bq')
        self.sec = gam.g4_units('second')
        self.user_info = source_info
        self.current_time = 1.0 * self.sec
        self.shot_event_count = 0
        self.total_event_count = gam.SourceManager.max_int
        self.run_timing_intervals = False
        self.current_run_interval = None
        self.required_keys = ['name', 'type', 'end_time', 'start_time']

    def __str__(self):
        r = [self.user_info.start_time, self.user_info.end_time]
        s = f'Source name        : {self.user_info.name}\n' \
            f'Source type        : {self.user_info.type}\n' \
            f'Start time         : {self.user_info.start_time / self.sec} sec\n' \
            f'End time           : {self.user_info.end_time / self.sec} sec\n' \
            f'Generated events   : {self.shot_event_count}\n' \
            f'Estim. total events: {self.get_estimated_number_of_events(r):.0f}'
        return s

    def __del__(self):
        print('destructor SourceBase')

    def check_user_info(self):
        # the list of required keys may be modified in the
        # classes that inherit from this one
        gam.assert_keys(self.required_keys, self.user_info)

    def set_current_run_interval(self, current_run_interval):
        self.current_run_interval = current_run_interval

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if 'start_time' not in self.user_info:
            self.user_info.start_time = run_timing_intervals[0][0]
        if 'end_time' not in self.user_info:
            self.user_info.end_time = run_timing_intervals[-1][1]
        if 'n' in self.user_info:
            self.total_event_count = self.user_info.n
        self.check_user_info()

    def get_estimated_number_of_events(self, run_timing_interval):
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
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

    def GeneratePrimaries(self, event, time):
        gam.fatal(f'SourceBase::GeneratePrimaries must be overloaded for source {self.user_info}')
