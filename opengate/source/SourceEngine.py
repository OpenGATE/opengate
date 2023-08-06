import opengate as gate
import opengate_core as g4
from box import Box


class SourceEngine(gate.EngineBase):
    """
    Source Engine manages the G4 objects of sources at runtime
    """

    # G4RunManager::BeamOn takes an int as input. The max cpp int value is currently 2147483647
    # Python manages int differently (no limit), so we need to set the max value here.
    max_int = 2147483647

    def __init__(self, simulation_engine):
        gate.EngineBase.__init__(self, simulation_engine)

        # Keep a pointer to the current simulation
        # self.source_manager = source_manager
        self.simulation_engine = simulation_engine

        # List of run time intervals
        self.run_timing_intervals = None
        self.current_run_interval = None

        # List of sources (GateSource), for all threads
        self.sources = []

        # The source manager will be constructed at build (during ActionManager)
        # Its task is to call GeneratePrimaries and loop over the sources
        # For MT, the master_source_manager is the MasterThread
        # The g4_thread_source_managers list all master sources for all threads
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = []

        # internal variables
        self.g4_particle_table = None

        # Options dict for cpp SourceManager
        # will be set in create_g4_source_manager
        self.source_manager_options = Box()

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting SourceEngine")

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing SourceEngine")
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_master_source_manager = None
        self.g4_thread_source_managers = None
        self.g4_particle_table = None
        self.sources = None  # a source object contains a reference to a G4 source

    def initialize(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        gate.assert_run_timing(self.run_timing_intervals)
        if len(self.simulation_engine.simulation.source_manager.user_info_sources) == 0:
            gate.warning(f"No source: no particle will be generated")

    def initialize_actors(self, actors):
        """
        Parameters
        ----------
        actors : dict
            The dictionary ActorEngine.actors which contains key-value pairs
            "actor_name" : "Actor object"
        """
        self.g4_master_source_manager.SetActors(list(actors.values()))

    def create_master_source_manager(self):
        # create particles table # FIXME in physics ??
        # NK: I don't think this is the correct approach
        # The particles are constructed through the RunManager when the
        # physics list is initialized, namely in G4RunManagerKernel::SetupPhysics()
        # self.g4_particle_table = g4.G4ParticleTable.GetParticleTable()
        # self.g4_particle_table.CreateAllParticles()  # Warning: this is a hard-coded list!
        # create the master source for the masterThread
        self.g4_master_source_manager = self.create_g4_source_manager(append=False)
        return self.g4_master_source_manager

    def create_g4_source_manager(self, append=True):
        """
        This is called by all threads
        This object is needed here, because it can only be
        created after physics initialization
        """
        ms = g4.GateSourceManager()
        # create all sources for this source manager (for all threads)
        for (
            vu
        ) in (
            self.simulation_engine.simulation.source_manager.user_info_sources.values()
        ):
            source = gate.new_element(vu, self.simulation_engine.simulation)
            ms.AddSource(source.g4_source)
            source.initialize(self.run_timing_intervals)
            self.sources.append(source)
        # taking __dict__ allow to consider the class SimulationUserInfo as a dict
        sui = self.simulation_engine.simulation.user_info.__dict__
        # warning: copy the simple elements from this dict (containing visu or verbose)
        for s in sui:
            if "visu" in s or "verbose_" in s:
                self.source_manager_options[s] = sui[s]
        ms.Initialize(self.run_timing_intervals, self.source_manager_options)
        # set the flag for user event info
        ms.fUserEventInformationFlag = (
            self.simulation_engine.user_event_information_flag
        )
        # keep pointer to avoid deletion
        if append:
            self.g4_thread_source_managers.append(ms)
        return ms

    def start(self):
        # FIXME (1) later : may replace BeamOn with DoEventLoop
        # to allow better control on geometry between the different runs
        # (2) : check estimated nb of particle, warning if too large
        # start the master thread (only main thread)
        self.g4_master_source_manager.StartMasterThread()

        # once terminated, packup the sources (if needed)
        for source in self.sources:
            source.prepare_output()
