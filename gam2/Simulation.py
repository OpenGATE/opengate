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
        # elements parameters (user defined)
        self.geometry = Box()
        self.physics = Box()
        self.sources = Box()
        self.actors = Box()
        # G4 elements
        self.g4_runManager = None
        self.g4_geometry = None
        self.g4_physics = None
        self.g4_source = None
        self.g4_action = None
        self.g4_random_engine = None
        self.g4_ui = None
        # internal state
        self.initialized = False
        # default elements
        self.ui = gam2.UIsessionSilent()
        #self.set_g4_output(self.ui)
        w = self.add_volume('Box', 'World')
        w.mother = None
        m = gam.g4_units('meter')
        w.size = [3*m, 3*m, 3*m]
        w.material = 'Air'

    def __del__(self):
        print('Simulation destructor')
        # del self.g4_runManager
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
        print('Initialize Geometry')
        self.g4_geometry = gam2.Geometry(self.geometry)
        self.g4_runManager.SetUserInitialization(self.g4_geometry)

        # phys
        print('Initialize Physics')

        factory = g4.G4PhysListFactory()
        l = factory.AvailablePhysLists()
        print(l)
        self.g4_physics = factory.GetReferencePhysList('QGSP_BERT_EMV')
        #print(self.g4_physics)
        self.g4_physics.DumpList()
        self.g4_physics.DumpCutValuesTable(1)
        print('default cut value', self.g4_physics.GetDefaultCutValue())
        #exit(0)
        #self.g4_physics = g4.QBBC(0, "QGSP_BERT_EMV")
        #self.g4_physics = g4.QBBC(0, "QBBC")
        # G4ProductionCutsTable::GetProductionCutsTable()->SetEnergyRange(limit, 100. * GeV);
        # like Gate (not useful) FIXME to remove
        pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
        print('pct', pct)
        eV = gam.g4_units('eV')
        GeV = gam.g4_units('GeV')
        pct.SetEnergyRange(250 * eV, 100 * GeV)
        print('default cut value', self.g4_physics.GetDefaultCutValue())
        self.g4_runManager.SetUserInitialization(self.g4_physics)
        self.g4_physics.DumpCutValuesTable(1)
        self.g4_physics.DumpCutValuesTableIfRequested()

        # sources = dic
        print('Initialize Source')
        self.g4_source = gam2.Source(self.sources)

        # action
        self.g4_action = gam2.Actions(self.g4_source)

        self.g4_runManager.SetUserInitialization(self.g4_action)
        # todo run/event/step

        # Initialization
        print('Before Initialize')
        self.g4_runManager.Initialize()
        print('After Initialize')
        self.initialized = True

        # Actors initialization
        self._initialize_actors()

        # FIXME
        self.g4_physics.DumpCutValuesTable(1)
        self.g4_physics.DumpCutValuesTableIfRequested()
        return

    def start(self):
        """
        Start the simulation
        """

        if not self.initialized:
            print('Error initialize before')

        ui = g4.G4UImanager.GetUIpointer()
        ui.ApplyCommand("/run/verbose 2")
        # ui.ApplyCommand("/tracking/verbose 1")
        print('Start ...')
        # self.Start()
        n = 30000
        n = 50000
        start = time.time()
        self.g4_runManager.BeamOn(n, None, -1)
        end = time.time()
        print('Timing BeamOn', end - start)
        # self.a.PrintDebug()
        # self.a2.PrintDebug()
        # self.a3.PrintDebug()

    def set_random_engine(self, engine_name, seed):
        # FIXME add more random engine later
        if engine_name != 'MersenneTwister':
            s = f'Cannot find the random engine {engine_name}\n'
            s += f'Use: MersenneTwister'
            gam.fatal(s)
        self.g4_random_engine = g4.MTwistEngine()
        g4.G4Random.setTheEngine(self.g4_random_engine)
        g4.G4Random.setTheSeeds(seed, 0)

    def set_g4_output(self, ui_session):
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
            actor.g4_actor = gam2.actor_build(actor)
            gam2.actor_register_actions(self, actor)