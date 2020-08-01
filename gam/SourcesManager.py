import sys
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

    def __init__(self, run_time_intervals, sources_info):
        g4.G4VUserPrimaryGeneratorAction.__init__(self)
        self.run_time_intervals = run_time_intervals
        self.sources_info = sources_info
        self.sim_time = 0
        self.current_run_id = 0
        self.current_run_interval = run_time_intervals[0]
        self.simulation = None

    def start(self, simulation):
        self.simulation = simulation
        # FIXME check estimated number of particles per run per source
        self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)
        #self.simulation.g4_RunManager.BeamOn(100, None, -1)

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
            if s.g4_UserPrimaryGenerator.is_terminated(self.sim_time):
                continue
            # get the next event time for this source
            source_time, event_id = s.g4_UserPrimaryGenerator.get_next_event_info(self.sim_time)
            # keep the lowest one
            # in case of equality, consider the event number
            if source_time < next_time or (source_time == next_time and event_id < next_event_id):
                next_time = source_time
                next_source = s
                next_event_id = event_id
        print('Selected next source ', next_time, next_source, next_event_id)
        return next_time, next_source

    def simulation_end(self):
        print('End of simulation', self.current_run_id)
        #self.simulation.g4_RunManager.AbortRun(True)  # True mean, terminate current event
        #self.simulation.g4_RunManager.RunTermination()
        # self.simulation.g4_RunManager.AbortRun(False)  # True mean, terminate current event
        print('beam ', self.simulation.g4_RunManager.ConfirmBeamOnCondition())

    def check_for_next_run(self):
        print('check_for_next_run', self.sim_time, self.current_run_interval)
        all_sources_terminated = True
        for source_info in self.sources_info.values():
            t = source_info.g4_UserPrimaryGenerator.is_terminated(self.sim_time)
            print(t)
            if not t:
                all_sources_terminated = False
                break
        if all_sources_terminated or self.sim_time > self.current_run_interval[1]:
            self.next_run()

    def next_run(self):
        print('end current run', self.sim_time, self.current_run_interval)
        # self.simulation.g4_RunManager.TerminateEventLoop()
        print('BEFORE RunTermination')
        # both are needed to enable restart
        self.simulation.g4_RunManager.AbortRun(False) # True mean, terminate current event
        self.simulation.g4_RunManager.RunTermination()
        print('AFTER RunTermination')

        # self.simulation.g4_RunManager.AbortRun(False)
        # print('beam ', self.simulation.g4_RunManager.ConfirmBeamOnCondition())
        self.current_run_id += 1
        if self.current_run_id >= len(self.run_time_intervals):
            self.simulation_end()
            return
        self.current_run_interval = self.run_time_intervals[self.current_run_id]
        self.simulation.prepare_for_next_run(self.sim_time, self.current_run_interval)
        print('new run will start', self.current_run_id)
        print('beam ', self.simulation.g4_RunManager.ConfirmBeamOnCondition())
        self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)

    def GeneratePrimaries(self, event):
        print('SourceManager GeneratePrimaries ', self.sim_time)

        # select the next source and the next time
        self.sim_time, next_source = self.get_next_event_info()

        # if no source are selected, the current run is terminated
        if not next_source:
            self.next_run()
            return

        # shoot the particle
        next_source.g4_UserPrimaryGenerator.GeneratePrimaries(event, self.sim_time)

        # check if the run is terminated ?
        self.check_for_next_run()
