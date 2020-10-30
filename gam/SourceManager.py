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


class SourceManager:
    """
    Manage all the sources in the simulation.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    # G4RunManager::BeamOn takes an int as input. The max cpp int value is currently 2147483647
    # Python manage int differently (no limit), so we need to set the max value here.
    max_int = 2147483647

    def __init__(self, simulation):
        self.simulation = simulation
        self.run_timing_intervals = None
        self.current_run_interval = None
        self.sources = {}
        # This master source will only be constructed at initialization.
        # Its only task is to call GeneratePrimaries
        self.g4_master_source = None
        self.next_active_source = None
        self.current_simulation_time = 0
        self.next_simulation_time = 0
        self.current_run_id = 0
        self.simulation_is_terminated = False
        # g4 objects
        self.particle_table = None
        # NEW FIXME

    def __str__(self):
        """
        str only dump the user info on a single line
        """
        v = [v.user_info.name for v in self.sources.values()]
        s = f'{" ".join(v)} ({len(self.sources)})'
        return s

    def __del__(self):
        print('SourceManager destructor')

    def dump(self, level):
        n = len(self.sources)
        s = f'Number of sources: {len(self.sources)}'
        if level < 1:
            for source in self.sources.values():
                a = f'\n {source.user_info}'
                s += gam.indent(2, a)
        else:
            for source in self.sources.values():
                a = f'\n{source.dump(level)}'
                s += gam.indent(2, a)
        return s

    def get_source(self, name):
        if name not in self.sources:
            gam.fatal(f'The source {name} is not in the current '
                      f'list of sources: {self.sources}')
        return self.sources[name]

    def add_source(self, source_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.sources, name)
        # build it
        s = gam.new_element('Source', source_type, name, self.simulation)
        # append to the list
        self.sources[name] = s
        # return the info
        return s.user_info

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        gam.assert_run_timing(self.run_timing_intervals)
        if len(self.sources) == 0:
            gam.fatal(f'No source: no particle will be generated')
        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        self.particle_table.CreateAllParticles()
        # FIXME check and sort self.run_timing_interval
        self.current_run_interval = run_timing_intervals[0]
        self.current_run_id = 0
        # This object is needed here, because can only be
        # created after physics initialization
        self.g4_master_source = gam.SourceMaster(self)
        for source in self.sources.values():
            log.info(f'Init source [{source.user_info.type}] {source.user_info.name}')
            source.initialize(self.run_timing_intervals)

    def start(self):
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        # FIXME (2) : check estimated nb of particle, warning if too large
        self.start_current_run()

    def start_current_run(self):
        # set the current time interval
        self.current_run_interval = self.run_timing_intervals[self.current_run_id]
        self.current_simulation_time = self.current_run_interval[0]
        # initialize run for all sources
        for source in self.sources.values():
            source.start_current_run(self.current_simulation_time, self.current_run_interval)
        # log
        est = 0
        for source in self.sources.values():
            est += source.get_estimated_number_of_events(self.current_run_interval)
        source_log.info(f'Start2 Run id {self.current_run_id} '
                        f'({self.current_run_id + 1}/{len(self.run_timing_intervals)})'
                        f' {gam.info_timing(self.current_run_interval)}'
                        f' estimated events for this run: {int(est)}')
        # check the engine is ready
        b = self.simulation.g4_RunManager.ConfirmBeamOnCondition()
        if not b:
            gam.fatal(f'Cannot start run, ConfirmBeamOnCondition is False')
        # init all the sources
        self.prepare_next_source()
        # special case for visualisation and GO !
        if self.simulation.g4_visualisation_flag:
            self.simulation.g4_apply_command(f'/run/beamOn {self.max_int}')
            self.simulation.g4_ui_executive.SessionStart()
            # FIXME after the session, when the window is closed, seg fault for the second run.
        else:
            self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)

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
        if self.next_simulation_time >= self.current_run_interval[1]:
            self.prepare_next_run()
            return
        all_sources_terminated = True
        for source in self.sources.values():
            t = source.source_is_terminated(self.current_simulation_time)
            if not t:
                all_sources_terminated = False
                break
        if not self.next_active_source:
            all_sources_terminated = True
        if all_sources_terminated:
            self.prepare_next_run()

    def prepare_next_source(self):
        min_time = self.current_run_interval[1]
        self.next_active_source = None
        for source in self.sources.values():
            t = source.source_is_terminated(self.current_simulation_time)
            if not t:
                next_time, next_event_id = source.get_next_event_info(self.current_simulation_time)
                if next_time < min_time:
                    min_time = next_time
                    self.next_active_source = source
        self.next_simulation_time = min_time

    def generate_primaries(self, event):
        """
        This function is called by: SourceMaster::GeneratePrimaries
        (G4VUserPrimaryGeneratorAction)

        When this function is called, we know that an event must be
        generated and we know the current active source.

        Once the event is shoot, the function 'prepare_next_source'
        will select the next active source.
        The function 'check_for_next_run' will check if the current
        RUN should be stopped.

        """

        # shoot the particle
        self.current_simulation_time = self.next_simulation_time
        source_log.debug(f'Run {self.current_run_id} '
                         f'Event {event.GetEventID()} '
                         f'{self.next_active_source.user_info.name} at '
                         f'{gam.g4_best_unit(self.current_simulation_time, "Time")}')
        self.next_active_source.generate_primaries(event, self.current_simulation_time)
        self.prepare_next_source()
        self.check_for_next_run()
