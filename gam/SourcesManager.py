import gam
import gam_g4 as g4


class SourcesManager(g4.G4VUserPrimaryGeneratorAction):
    """
    Implement G4VUserPrimaryGeneratorAction.
    The function GeneratePrimaries will be called by Geant4 engine.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    # G4RunManager::BeamOn takes an int as input. The max cpp int value is currently 2147483647
    # Python manage int differently (no limit), so we need to set the max value here.
    max_int = 2147483647

    def __init__(self, run_timing_intervals, sources_info):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        self.run_timing_intervals = run_timing_intervals
        self.sources_info = sources_info
        self.sim_time = 0
        self.current_run_id = 0
        self.current_run_interval = run_timing_intervals[0]
        self.simulation = None
        self.sec = gam.g4_units('second')

    def start(self, simulation):
        self.simulation = simulation
        gam.assert_all_sources(simulation)
        gam.assert_run_timing(simulation.run_timing_intervals)
        # FIXME later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)

    def get_next_event_info(self):
        """
        Return the next source and its associated time
        Consider the current time and loop over all the sources. Select the one
        with the lowest next time, or, in case of equality, the one with the
        lowest event id.
        """
        next_time = self.current_run_interval[1]  # max time for the current interval
        next_event_id = self.max_int
        next_source = None  # self.sources_info.values()[0] #None
        for s in self.sources_info.values():
            # do not check terminated source
            if s.g4_PrimaryGenerator.is_terminated(self.sim_time):
                continue
            # get the next event time for this source
            source_time, event_id = s.g4_PrimaryGenerator.get_next_event_info(self.sim_time)
            # keep the lowest one, in case of equality, consider the event number
            if source_time < next_time or (source_time == next_time and event_id < next_event_id):
                next_time = source_time
                next_source = s
                next_event_id = event_id
        return next_time, next_source

    def simulation_end(self):
        print('End of simulation', self.current_run_id)
        # self.simulation.g4_RunManager.AbortRun(True)  # True mean, terminate current event
        # self.simulation.g4_RunManager.RunTermination()
        # self.simulation.g4_RunManager.AbortRun(False)  # True mean, terminate current event
        print('beam ', self.simulation.g4_RunManager.ConfirmBeamOnCondition())

    def check_for_next_run(self):
        all_sources_terminated = True
        for source_info in self.sources_info.values():
            t = source_info.g4_PrimaryGenerator.is_terminated(self.sim_time)
            if not t:
                all_sources_terminated = False
                break
        if all_sources_terminated or self.sim_time > self.current_run_interval[1]:
            self.next_run()

    def next_run(self):
        # both AbortRun and RunTermination are needed to enable stop and restart
        self.simulation.g4_RunManager.AbortRun(True)  # True : means terminate current event
        self.simulation.g4_RunManager.RunTermination()

        # next run or end of simulation ?
        self.current_run_id += 1
        if self.current_run_id >= len(self.run_timing_intervals):
            self.simulation_end()
            return
        self.current_run_interval = self.run_timing_intervals[self.current_run_id]
        self.simulation.prepare_for_next_run(self.sim_time, self.current_run_interval)
        print('new run will start', self.current_run_id, self.current_run_interval)
        self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)

    def GeneratePrimaries(self, event):
        # print('SourceManager GeneratePrimaries ', self.sim_time)

        # select the next source and the next time
        self.sim_time, next_source = self.get_next_event_info()

        # if no source are selected, terminate the current run
        # Important: sometimes the smallest next time of all sources
        # may be larger than the end time of the current run
        if not next_source:
            self.next_run()
            return

        # shoot the particle
        print(f'New event id {event.GetEventID()}, {next_source.g4_PrimaryGenerator.shot_particle_count} '
              f'from {next_source.name} at time {self.sim_time / self.sec}')
        next_source.g4_PrimaryGenerator.GeneratePrimaries(event, self.sim_time)

        # check if the run is terminated ?
        self.check_for_next_run()
