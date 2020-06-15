from box import Box

import gam  # needed for gam_setup
import geant4 as g4
import gam2
import time


class Simulation:
    """
    TODO
    """

    def __init__(self, name='simulation'):
        """
        TODO
        """
        self.name = name
        self.g4_runManager = None
        self.g4_geometry = None
        self.g4_physics = None
        self.g4_source = None
        self.g4_action = None
        self.geometry = Box()
        self.actors = Box()
        self.initialized = False

    def __del__(self):
        print('Simulation destructor')
        #del self.g4_runManager


    def __str__(self):
        """
        Print a Simulation
        :return: a string
        """
        s = f'Simulation name: {self.name}'
        return s

    def initialize(self):
        """
        Build the simulation
        """
        print('Initialize simulation')
        self.g4_runManager = g4.G4RunManager()
        self.g4_runManager.SetVerboseLevel(0)

        # TODO : reset, start from scratch
        if self.initialized:
            print('Already initialized. Abort')
            exit(0)

        # geometry = dic
        self.g4_geometry = gam2.Geometry(self.geometry)
        self.g4_runManager.SetUserInitialization(self.g4_geometry)

        # phys
        self.g4_physics = g4.QBBC(0, "QBBC")
        self.g4_runManager.SetUserInitialization(self.g4_physics)

        # source
        self.g4_source = gam2.Source()

        # actor -> Run / Event / Track / Step
        self.g4_actors = gam2.Actor(self.actors)

        # action
        self.g4_action = gam2.Action(self.g4_source, self.g4_actors)
        self.g4_runManager.SetUserInitialization(self.g4_action)
        # todo run/event/step

        # Initialization
        print('Before Initialize')
        self.g4_runManager.Initialize()
        print('After Initialize')
        self.initialized = True

        # FIXME
        self.a = g4.GateTestActor()
        print('test actor', self.a)
        print('ln', len(self.g4_geometry.g4_logical_volumes))
        self.lv = self.g4_geometry.g4_logical_volumes['Waterbox']
        print('lv wb', self.lv)
        self.a.RegisterSD(self.lv)

    def start(self):
        """
        Start the simulation
        """
        self.initialize()
        ui = g4.G4UImanager.GetUIpointer()
        ui.ApplyCommand("/run/verbose 2")
        # ui.ApplyCommand("/tracking/verbose 1")
        print('Start ...')
        # self.Start()
        n = 30000
        n = 50#00
        start = time.time()
        self.g4_runManager.BeamOn(n, None, -1)
        end = time.time()
        print('Timing', end - start)
        self.a.PrintDebug()
