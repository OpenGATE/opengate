from box import Box
import gam  # needed for gam_setup
from gam import log
import gam_g4 as g4
import time
import random
import sys


class Simulation:
    """
    Main class that store and build a simulation.
    """

    def __init__(self, name='simulation'):
        """
        Constructor. Main members are:
        - dict-like description of the simulation (geometry, physics, sources, actors)
        - Geant4 objects that will be build during initialisation (start with g4_)
        - some internal variables
        """
        self.name = name

        # elements parameters (user defined)
        self.geometry = Box()
        self.physics = Box()
        self.sources = Box()
        self.actors = Box()
        self.geant4_verbose_level = 0

        # temporary DEBUG FIXME
        self.n = 500

        # G4 elements
        self.g4_RunManager = None
        self.g4_UserDetectorConstruction = None
        self.g4_PhysList = None
        self.g4_UserPrimaryGenerator = None
        self.g4_UserActionInitialization = None
        self.g4_HepRandomEngine = None

        # internal state
        self.initialized = False

        # default elements
        self._default_elements()

    def __del__(self):
        # del self.g4_RunManager ?
        # The following allow to remove the final warning
        g4.G4GeometryManager.GetInstance().OpenGeometry(None)

    def __str__(self):
        """
        Print a Simulation
        :return: a string
        """
        s = f'Simulation name: {self.name} \n' \
            f'Geometry: {self.geometry}\n' \
            f'Physics: {self.physics}\n' \
            f'Sources: {self.sources}\n' \
            f'Actors: {self.actors}\n'
        return s

    def _default_elements(self):
        """
        Internal. Build default elements: verbose, World, seed, physics
        """
        # G4 output
        self.disable_g4_output()
        self.geant4_verbose_level = 1
        # World volume
        w = self.add_volume('Box', 'World')
        w.mother = None
        m = gam.g4_units('meter')
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = 'Air'
        # seed
        self.physics.seed = 'auto'
        # physics default
        self.physics.name = 'QGSP_BERT_EMV'

    @staticmethod
    def get_available_physicLists():
        factory = g4.G4PhysListFactory()
        return factory.AvailablePhysLists()

    def initialize(self):
        """
        Build the main geant4 objects
        """
        log.info('Simulation : create G4RunManager')
        self.g4_RunManager = g4.G4RunManager()
        self.g4_RunManager.SetVerboseLevel(self.geant4_verbose_level)

        # Cannot be initialized two times (ftm)
        if self.initialized:
            gam.fatal('Simulation already initialized. Abort')

        # geometry = dic
        log.info('Simulation : initialize Geometry')
        self.g4_UserDetectorConstruction = gam.Geometry(self.geometry)
        self.g4_RunManager.SetUserInitialization(self.g4_UserDetectorConstruction)

        # phys
        log.info('Simulation : initialize Physics')
        self.g4_PhysList = gam.create_phys_list(self.physics)
        self.g4_RunManager.SetUserInitialization(self.g4_PhysList)
        gam.set_cuts(self.physics, self.g4_PhysList)

        # sources = dic
        log.info('Simulation : initialize Source')
        # self.g4_UserPrimaryGenerator = gam.Source(self.sources)
        if len(self.sources) is not 1:
            gam.fatal(f'One single source for the moment')
        k = list(self.sources)[0]
        source = self.sources[k]
        self.g4_UserPrimaryGenerator = gam.source_build(source)

        # action
        log.info('Simulation : initialize Actions')
        self.g4_UserActionInitialization = gam.Actions(self.g4_UserPrimaryGenerator) # FIXME source ?
        self.g4_RunManager.SetUserInitialization(self.g4_UserActionInitialization)

        # Initialization
        log.info('Simulation : initialize G4RunManager')
        self.g4_RunManager.Initialize()
        self.initialized = True

        # Actors initialization
        log.info('Simulation : initialize actors')
        self._initialize_actors()

        return

    def g4_com(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.initialized:
            gam.fatal(f'Please, use g4_com *after* simulation.initialize()')
        ui = g4.G4UImanager.GetUIpointer()
        ui.ApplyCommand(command)

    def dump_geometry_tree(self):
        s = self.g4_UserDetectorConstruction.dump_tree()
        return s

    def start(self):
        """
        Start the simulation
        """

        if not self.initialized:
            print('Error initialize before')

        print('Start ...', self.n)
        start = time.time()
        self.g4_RunManager.BeamOn(self.n, None, -1)
        end = time.time()
        print(f'Timing BeamOn {end - start} and PPS = {self.n/(end-start)}')

    def set_random_engine(self, engine_name, seed='auto'):
        # FIXME add more random engine later
        if engine_name != 'MersenneTwister':
            s = f'Cannot find the random engine {engine_name}\n'
            s += f'Use: MersenneTwister'
            gam.fatal(s)
        self.g4_HepRandomEngine = g4.MTwistEngine()
        g4.G4Random.setTheEngine(self.g4_HepRandomEngine)
        self.physics.seed = seed
        if seed == 'auto':
            self.physics.seed = random.randrange(sys.maxsize)
        g4.G4Random.setTheSeeds(self.physics.seed, 0)

    def disable_g4_output(self):
        ui = gam.UIsessionSilent()
        self.set_g4_ui_output(ui)

    def enable_g4_output(self, b=True):
        if not b:
            self.disable_g4_output()
        else:
            self.set_g4_ui_output(None)

    def set_g4_ui_output(self, ui_session):
        self.ui_session = ui_session
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.SetCoutDestination(ui_session)

    def _add_element(self, elements, element_type, element_name):
        if element_name in elements:
            s = f"Error, cannot add '{element_name}' because an element already exists" \
                f' in: {elements}.'
            gam.fatal(s)
        elements[element_name] = Box()
        e = elements[element_name]
        e.name = element_name
        e.type = element_type
        return e

    def add_volume(self, vol_type, name):
        v = self._add_element(self.geometry, vol_type, name)
        v.mother = 'World'
        return v

    def add_source(self, source_type, name):
        s = self._add_element(self.sources, source_type, name)
        return s

    def add_actor(self, actor_type, name):
        a = self._add_element(self.actors, actor_type, name)
        a.attachedTo = 'World'
        return a

    def _initialize_actors(self):
        for actor in self.actors.values():
            print('Create actor', actor.type, actor.name)
            actor.g4_actor = gam.actor_build(actor)
            gam.actor_register_actions(self, actor)
