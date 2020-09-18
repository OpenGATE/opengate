import gam
import gam_g4 as g4
import logging
import colorlog
from gam import log

"""
 log object for source
 use gam.source_log.setLevel(gam.RUN)
 or gam.source_log.setLevel(gam.EVENT)
 to print every run and/or event
"""
RUN = logging.INFO
EVENT = logging.DEBUG
source_log = colorlog.getLogger('gam_source')
source_log.addHandler(gam.handler)
source_log.setLevel(RUN)


class SourceManager(g4.G4VUserPrimaryGeneratorAction):
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
        self.simulation_is_terminated = False
        self.sec = gam.g4_units('second')

    def dump(self):
        si = self.sources_info
        s = f''
        for source in si.values():
            if len(si) > 1:
                a = '\n' + '-' * 20
            else:
                a = ''
            a += '\n' + str(source.g4_source)
            s += gam.indent(2, a)
        return s

    def initialize(self):
        # FIXME check and sort self.run_timing_interval
        for source_info in self.sources_info.values():
            log.info(f'Init source [{source_info.type}] {source_info.name}')
            source_info.g4_source = gam.source_build(source_info)
            source_info.g4_source.initialize(self.run_timing_intervals)

    def start(self, simulation):
        self.simulation = simulation

        # FIXME to put in source manager
        gam.assert_run_timing(simulation.run_timing_intervals)

        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        # FIXME (2) : check estimated nb of particle, warning if too large
        self.current_run_id = 0
        self.start_run()

    def start_run(self):
        self.current_run_interval = self.run_timing_intervals[self.current_run_id]
        self.simulation.prepare_for_next_run(self.sim_time, self.current_run_interval)
        source_log.info(f'Start2 Run id {self.current_run_id} '
                        f'({self.current_run_id + 1}/{len(self.run_timing_intervals)})'
                        f' {gam.info_timing(self.current_run_interval)}')
        b = self.simulation.g4_RunManager.ConfirmBeamOnCondition()
        if not b:
            gam.fatal(f'Cannot start run, ConfirmBeamOnCondition is False')
        for s in self.sources_info.values():
            s.g4_source.set_current_run_interval(self.current_run_interval)

        if self.simulation.g4_visualisation_flag:
            self.simulation.g4_apply_command(f'/run/beamOn {self.max_int}')
            self.simulation.g4_ui_executive.SessionStart()
            # FIXME after the session, when the window is closed, seg fault for the second run.
        else:
            self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)

    def get_next_event_info(self):
        """
        Return the next source and its associated time
        Consider the current time and loop over all the sources. Select the one
        with the lowest next time, or, in case of equality, the one with the
        lowest event id.
        """
        # by default the max next_time is the
        # end time of  the current interval
        next_time = self.current_run_interval[1]
        next_event_id = self.max_int
        next_source = None
        for s in self.sources_info.values():
            # do not check source that are terminated
            if s.g4_source.source_is_terminated(self.sim_time):
                continue
            # get the next event time for this source
            source_time, event_id = s.g4_source.get_next_event_info(self.sim_time)
            # keep the lowest one, in case of equality, consider the event number
            if source_time < next_time or (source_time == next_time and event_id < next_event_id):
                next_time = source_time
                next_source = s
                next_event_id = event_id

        return next_time, next_source

    def prepare_next_run(self):
        """
        Terminate the current run and check if there is a
        new run to start or end the simulation
        """
        # AbortRun True : means terminate current event
        self.simulation.g4_RunManager.AbortRun(True)

        # next run ?
        self.current_run_id += 1
        if self.current_run_id >= len(self.run_timing_intervals):
            self.stop_simulation()

    def stop_simulation(self):
        # FIXME  Later add a callback for EndOfSimulation
        self.simulation_is_terminated = True

    def check_for_next_run(self):
        all_sources_terminated = True
        for source_info in self.sources_info.values():
            t = source_info.g4_source.source_is_terminated(self.sim_time)
            if not t:
                all_sources_terminated = False
                break
        if all_sources_terminated or self.sim_time > self.current_run_interval[1]:
            self.prepare_next_run()

    def GeneratePrimaries(self, event):
        # select the next source and the next time
        self.sim_time, next_source = self.get_next_event_info()

        # if no source are selected, terminate the current run
        # Important: sometimes the smallest next time of all sources
        # may be larger than the end time of the current run.
        if not next_source:
            self.prepare_next_run()
            return

        # shoot the particle
        source_log.debug(f'New event id {event.GetEventID()} '
                         f'{next_source.name} at {gam.g4_best_unit(self.sim_time, "Time")}')
        next_source.g4_source.GeneratePrimaries(event, self.sim_time)

        # check if the run is terminated ?
        self.check_for_next_run()
