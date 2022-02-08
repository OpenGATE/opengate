import gam_gate as gam
import gam_g4 as g4
from box import Box


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
        # List of sources user info
        self.user_info_sources = {}
        # List of sources (GamSource), for all threads
        self.sources = []
        # The source manager will be constructed at build (during ActionManager)
        # Its task is to call GeneratePrimaries and loop over the sources
        # For MT, the master_source_manager is the MasterThread
        # The g4_thread_source_managers list all master source for all threads
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = []
        # internal variables
        self.particle_table = None
        # Options dict for cpp SourceManager
        # will be set in create_g4_source_manager
        self.source_manager_options = Box()

    def __str__(self):
        """
        str only dump the user info on a single line
        """
        v = [v.name for v in self.user_info_sources.values()]
        s = f'{" ".join(v)} ({len(self.user_info_sources)})'
        return s

    def __del__(self):
        pass

    def dump(self):
        n = len(self.user_info_sources)
        s = f'Number of sources: {n}'
        for source in self.user_info_sources.values():
            a = f'\n {source}'
            s += gam.indent(2, a)
        return s

    def get_source_info(self, name):
        if name not in self.user_info_sources:
            gam.fatal(f'The source {name} is not in the current '
                      f'list of sources: {self.user_info_sources}')
        return self.user_info_sources[name]

    def get_source(self, name):
        n = len(self.g4_thread_source_managers)
        if n > 0:
            gam.warning(f'Cannot get source in multithread mode, use get_source_MT')
            return None
        for source in self.sources:
            if source.user_info.name == name:
                return source.g4_source
        gam.fatal(f'The source {name} is not in the current '
                  f'list of sources: {self.user_info_sources}')

    def get_source_MT(self, name, thread):
        n = len(self.g4_thread_source_managers)
        if n == 0:
            gam.warning(f'Cannot get source in mono-thread mode, use get_source')
            return None
        i = 0
        for source in self.sources:
            if source.user_info.name == name:
                if i == thread:
                    return source.g4_source
                i += 1
        gam.fatal(f'The source {name} is not in the current '
                  f'list of sources: {self.user_info_sources}')

    def add_source(self, source_type, name):
        # check that another element with the same name does not already exist
        gam.assert_unique_element_name(self.user_info_sources, name)
        # init the user info
        s = gam.UserInfo('Source', source_type, name)
        # append to the list
        self.user_info_sources[name] = s
        # return the info
        return s

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        gam.assert_run_timing(self.run_timing_intervals)
        if len(self.user_info_sources) == 0:
            gam.fatal(f'No source: no particle will be generated')

    def build(self):
        # create particles table # FIXME in physics ??
        self.particle_table = g4.G4ParticleTable.GetParticleTable()
        self.particle_table.CreateAllParticles()
        # create the master source for the masterThread
        self.g4_master_source_manager = self.create_g4_source_manager(False)
        return self.g4_master_source_manager

    def create_g4_source_manager(self, append=True):
        # -----------------------------
        # This is called by all threads
        # -----------------------------
        # This object is needed here, because it can only be
        # created after physics initialization
        ms = g4.GamSourceManager()
        # create all sources for this source manager (for all threads)
        for vu in self.user_info_sources.values():
            source = gam.new_element(vu, self.simulation)
            ms.AddSource(source.g4_source)
            source.initialize(self.run_timing_intervals)
            self.sources.append(source)
        # taking __dict__ allow to consider the class SimulationUserInfo as a dict
        sui = self.simulation.user_info.__dict__
        # warning: copy the simple elements from this dict (containing visu or verbose)
        for s in sui:
            if 'visu' in s or 'verbose_' in s:
                self.source_manager_options[s] = sui[s]
        ms.Initialize(self.run_timing_intervals, self.source_manager_options)
        # keep pointer to avoid deletion
        if append:
            self.g4_thread_source_managers.append(ms)
        return ms

    def start(self):
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # FIXME to allow better control on geometry between the different runs
        # FIXME (2) : check estimated nb of particle, warning if too large
        # start the master thread (only main thread)
        self.g4_master_source_manager.StartMasterThread()
