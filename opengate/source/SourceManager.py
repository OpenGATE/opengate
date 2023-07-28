import opengate as gate
import opengate_core as g4


class SourceManager:
    """
    Manage all the sources in the simulation.
    The function prepare_generate_primaries will be called during
    the main run loop to set the current time and source.
    """

    def __init__(self, simulation):
        # Keep a pointer to the current simulation
        self.simulation = simulation
        # List of run times intervals
        self.run_timing_intervals = None
        self.current_run_interval = None
        # List of sources user info
        self.user_info_sources = {}

    def __str__(self):
        """
        Dump the user info on a single line
        """
        v = [v.name for v in self.user_info_sources.values()]
        s = f'{" ".join(v)} ({len(self.user_info_sources)})'
        return s

    def __del__(self):
        # print("del SourceManager")
        pass

    def dump(self):
        n = len(self.user_info_sources)
        s = f"Number of sources: {n}"
        for source in self.user_info_sources.values():
            a = f"\n {source}"
            s += gate.indent(2, a)
        return s

    def get_source_info(self, name):
        if name not in self.user_info_sources:
            gate.fatal(
                f"The source {name} is not in the current "
                f"list of sources: {self.user_info_sources}"
            )
        return self.user_info_sources[name]

    def add_source(self, source_type, name):
        # check that another element with the same name does not already exist
        gate.assert_unique_element_name(self.user_info_sources, name)
        # init the user info
        s = gate.UserInfo("Source", source_type, name)
        # append to the list
        self.user_info_sources[name] = s
        # return the info
        return s

    def initialize_before_g4_engine(self):
        for source in self.user_info_sources.values():
            if source.initialize_before_g4_engine:
                source.initialize_before_g4_engine(source)
