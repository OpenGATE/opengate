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
        self.pid = os.getpid()
        self.ppid = os.getppid()
        self.current_random_seed = None

    def __del__(self):
        # print("del SimulationOutput")
        pass

    def get_actor(self, name):
        if name not in self.actors:
            s = self.actors.keys
            gate.fatal(
                f'The actor "{name}" does not exist. Here is the list of actors: {s}'
            )
        return self.actors[name]
