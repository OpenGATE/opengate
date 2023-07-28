class EngineBase:
    """
    Base class for all engines (SimulationEngine, VolumeEngine, etc.)
    """

    def __init__(self):
        # debug verbose
        self.verbose_destructor = False

    def __del__(self):
        if self.verbose_destructor:
            print("del EngineBase")
