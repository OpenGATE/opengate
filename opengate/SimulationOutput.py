from .ExceptionHandler import *
import os


class SimulationOutput:
    """
    FIXME
    """

    def __init__(self):
        self.simulation = None
        self.actors = {}
        self.sources = {}
        self.sources_by_thread = {}
        self.pid = os.getpid()
        self.ppid = os.getppid()
        self.current_random_seed = None

    def __del__(self):
        pass

    def store_actors(self, simulation_engine):
        self.actors = simulation_engine.actor_engine.actors

    def store_sources(self, simulation_engine):
        self.sources = {}
        s = {}
        source_engine = simulation_engine.source_engine
        ui = simulation_engine.simulation.user_info
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            th = {}
            self.sources_by_thread = [{}] * (ui.number_of_threads + 1)
            for source in source_engine.sources:
                n = source.user_info.name
                if n in th:
                    th[n] += 1
                else:
                    th[n] = 0
                self.sources_by_thread[th[n]][n] = source
        else:
            for source in source_engine.sources:
                s[source.user_info.name] = source
            self.sources = s

    def get_actor(self, name):
        if name not in self.actors:
            s = self.actors.keys
            gate.fatal(
                f'The actor "{name}" does not exist. Here is the list of actors: {s}'
            )
        return self.actors[name]

    def get_source(self, name):
        ui = self.simulation.user_info
        if ui.number_of_threads > 1 or ui.force_multithread_mode:
            return self.get_source_MT(name, 0)
        if name not in self.sources:
            s = self.sources.keys
            gate.fatal(
                f'The source "{name}" does not exist. Here is the list of sources: {s}'
            )
        return self.sources[name]

    def get_source_MT(self, name, thread):
        ui = self.simulation.user_info
        if ui.number_of_threads <= 1 and not ui.force_multithread_mode:
            gate.fatal(f"Cannot use get_source_MT in monothread mode")
        if thread >= len(self.sources_by_thread):
            gate.fatal(
                f"Cannot get source {name} with thread {thread}, while "
                f"there are only {len(self.sources_by_thread)} threads"
            )
        if name not in self.sources_by_thread[thread]:
            s = self.sources_by_thread[thread].keys
            gate.fatal(
                f'The source "{name}" does not exist. Here is the list of sources: {s}'
            )
        return self.sources_by_thread[thread][name]
