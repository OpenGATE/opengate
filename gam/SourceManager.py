import gam
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
        self.sim_time = 0
        self.current_run_id = 0
        self.simulation_is_terminated = False

    def __str__(self):
        return self.dump()

    def dump(self):
        n = len(self.sources)
        s = f'Number of sources: {len(self.sources)}'
        for source in self.sources.values():
            if n > 1:
                a = '\n' + '-' * 20
            else:
                a = ''
            a += '\n' + str(source)
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
        builder = gam.get_source_builder(source_type)
        s = builder(name)
        # required to set the simulation pointer FIXME (how to automatize ?)
        s.set_simulation(self.simulation)
        # required to set the default list of keys FIXME (how to automatize ?)
        s.initialize_keys()
        # append to the list
        self.sources[name] = s
        # return the info
        return s.user_info

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        self.current_run_interval = run_timing_intervals[0]
        self.g4_master_source = gam.SourceMaster(self)
        # FIXME check and sort self.run_timing_interval
        for source in self.sources.values():
            log.info(f'Init source [{source.user_info.type}] {source.user_info.name}')
            source.initialize(self.run_timing_intervals)

    def start(self):
        gam.assert_run_timing(self.run_timing_intervals)
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        # FIXME (2) : check estimated nb of particle, warning if too large
        self.current_run_id = 0
        self.start_run()

    def prepare_for_next_run(self):
        # print('FIXME prepare next run for geometry')
        # http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomDynamic.html
        # G4RunManager::GeometryHasBeenModified();
        # OR Rather -> Open Close geometry for all volumes for which it is required
        for source in self.sources.values():
            source.prepare_for_next_run(self.sim_time, self.current_run_interval)

    def start_run(self):
        self.current_run_interval = self.run_timing_intervals[self.current_run_id]
        self.prepare_for_next_run()
        est = 0
        for source in self.sources.values():
            est += source.get_estimated_number_of_events(self.current_run_interval)
        source_log.info(f'Start2 Run id {self.current_run_id} '
                        f'({self.current_run_id + 1}/{len(self.run_timing_intervals)})'
                        f' {gam.info_timing(self.current_run_interval)}'
                        f' estimated primaries: {int(est)}'
                        f' ({len(self.sources.values())} source(s))')
        b = self.simulation.g4_RunManager.ConfirmBeamOnCondition()
        if not b:
            gam.fatal(f'Cannot start run, ConfirmBeamOnCondition is False')
        for source in self.sources.values():
            source.set_current_run_interval(self.current_run_interval)

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
        for source in self.sources.values():
            # do not check source that are terminated
            if source.source_is_terminated(self.sim_time):
                continue
            # get the next event time for this source
            source_time, event_id = source.get_next_event_info(self.sim_time)
            # keep the lowest one, in case of equality, consider the event number
            if source_time < next_time or (source_time == next_time and event_id < next_event_id):
                next_time = source_time
                next_source = source
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
        for source in self.sources.values():
            t = source.source_is_terminated(self.sim_time)
            if not t:
                all_sources_terminated = False
                break
        if all_sources_terminated or self.sim_time > self.current_run_interval[1]:
            self.prepare_next_run()

    def generate_primaries(self, event):
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
                         f'{next_source.user_info.name} at {gam.g4_best_unit(self.sim_time, "Time")}')
        next_source.generate_primaries(event, self.sim_time)

        # check if the run is terminated ?
        self.check_for_next_run()
