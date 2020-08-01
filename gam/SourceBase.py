import gam
import gam_g4 as g4


class SourceBase(g4.G4VUserPrimaryGeneratorAction):

    def __init__(self, source_info):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        print('SourceBase const', source_info)
        self.Bq = gam.g4_units('Bq')
        self.sec = gam.g4_units('second')
        self.source_info = source_info
        self.current_time = 1.0 * self.sec
        self.shot_particle_count = 0
        self.total_particle_count = gam.SourcesManager.max_int
        self.run_time_intervals = False
        # FIXME check both n and activity !!


    def __str__(self):
        r = [self.source_info.start_time, self.source_info.end_time]
        s = f'Source name     : {self.source_info.name}\n' \
            f'Source type     : {self.source_info.type}\n' \
            f'Start time      : {self.source_info.start_time / self.sec} sec\n' \
            f'End time        : {self.source_info.end_time / self.sec} sec\n' \
            f'Generated event : {self.shot_particle_count}\n' \
            f'Events (estim)  : {self.get_estimated_number_of_events(r)}'
        return s

    def initialize(self, run_time_intervals):
        print('SourceBase init', run_time_intervals)
        self.run_time_intervals = run_time_intervals
        # by default consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if 'start_time' not in self.source_info:
            self.source_info.start_time = run_time_intervals[0][0]
        if 'end_time' not in self.source_info:
            self.source_info.end_time = run_time_intervals[-1][1]
        if 'n' in self.source_info:
            self.total_particle_count = self.source_info.n

    def get_estimated_number_of_events(self, run_time_interval):
        # by default, all event have the same time, so we check that
        # this time is included into the given time interval
        if run_time_interval[0] <= self.source_info.start_time <= run_time_interval[1]:
            return self.total_particle_count
        return 0

    def prepare_for_next_run(self, sim_time, current_run_interval):
        # some sources may need this function
        pass

    def is_terminated(self, sim_time):
        print(f'SourceBase is_terminated {self.source_info.name} -> '
              f'time: {sim_time / self.sec} - {self.source_info.end_time / self.sec} '
              f'particles {self.shot_particle_count}/{self.total_particle_count}')
        # By default, the source if terminated if the time is larger than the end time
        if sim_time > self.source_info.end_time:
            return True
        # if this is not the case, it can still be terminated
        # if a max number of event is reached
        if self.shot_particle_count >= self.total_particle_count:
            return True
        return False

    def get_next_event_info(self, time):
        gam.fatal(f'SourceBase::prepare_generate_primaries must be overloaded for source {self.source_info}')
        # return 0, 0 ## return next_time and next_event_id

    def GeneratePrimaries(self, event, time):
        gam.fatal(f'SourceBase::GeneratePrimaries must be overloaded for source {self.source_info}')
