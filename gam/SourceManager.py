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
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # List of run times intervals
        self.run_timing_intervals = None
        self.current_run_interval = None
        # List of sources (GamSource)
        self.sources = {}
        # Keep all sources (for all threads) to avoid pointer deletion
        self.g4_sources = []
        # The source manager will be constructed at build (during ActionManager)
        # Its task is to call GeneratePrimaries and loop over the sources
        # For MT, the master_source_manager is the MasterThread
        # The g4_thread_source_managers list all master source for all threads
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = []
        # internal variables
        self.particle_table = None

    def __str__(self):
        """
        str only dump the user info on a single line
        """
        v = [v.user_info.name for v in self.sources.values()]
        s = f'{" ".join(v)} ({len(self.sources)})'
        return s

    def __del__(self):
        print('SourceManager destructor')
        for s in self.g4_sources:
            print('still a g4 source', s)
        for s in self.sources:
            print('still source', s)

    def dump(self, level):
        n = len(self.sources)
        s = f'Number of sources: {n}'
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
        # build it (note that the G4 counterpart of the source is not created yet)
        # it will be created by create_g4_source during build
        s = gam.new_element('Source', source_type, name, self.simulation)
        # append to the list
        self.sources[name] = s
        # return the info
        return s.user_info

    def build(self):
        gam.assert_run_timing(self.run_timing_intervals)
        if len(self.sources) == 0:
            gam.fatal(f'No source: no particle will be generated')
        # create particles table
        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        self.particle_table.CreateAllParticles()
        # create the master source for the masterThread
        self.g4_master_source_manager = self.create_g4_source_manager(False)
        return self.g4_master_source_manager

    def create_g4_source_manager(self, append=True):
        # This object is needed here, because can only be
        # created after physics initialization
        ms = g4.GamSourceManager()
        # set the source to the cpp side
        for source in self.sources.values():
            s = source.create_g4_source()
            # keep pointer to avoid delete
            self.g4_sources.append(s)
            # add the source to the source manager
            ms.AddSource(source.g4_source)
        # initialize the source master
        ms.Initialize(self.run_timing_intervals)
        for source in self.sources.values():
            s  =''
            if append:
                s = f' thread {len(self.g4_thread_source_managers)+1}'
            log.debug(f'Source{s}: initialize [{source.user_info.type}] {source.user_info.name}')
            source.initialize(self.run_timing_intervals)
        # keep pointer to avoid deletion
        if append:
            self.g4_thread_source_managers.append(ms)
        return ms

    def start(self):
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        # FIXME (2) : check estimated nb of particle, warning if too large

        # start the master thread (only main thread)
        self.g4_master_source_manager.StartMainThread()

        if self.simulation.g4_visualisation_flag:
            self.simulation.g4_ui_executive.SessionStart()

        # special case for visualisation and GO !
        #    if self.simulation.g4_visualisation_flag:
        #        self.simulation.g4_apply_command(f'/run/beamOn {self.max_int}')
        #        self.simulation.g4_ui_executive.SessionStart()
        #        # FIXME after the session, when the window is closed, seg fault for the second run.
        #    else:
        #        self.simulation.g4_RunManager.BeamOn(self.max_int, None, -1)
