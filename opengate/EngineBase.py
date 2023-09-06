class EngineBase:
    """
    Base class for all engines (SimulationEngine, VolumeEngine, etc.)
    """

    def __init__(self, simulation_engine):
        self.simulation_engine = simulation_engine
        # debug verbose
        self.verbose_destructor = simulation_engine.simulation.verbose_destructor
        self.verbose_getstate = simulation_engine.simulation.verbose_getstate
        self.verbose_close = simulation_engine.simulation.verbose_close
