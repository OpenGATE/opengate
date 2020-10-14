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

        # user's defined parameters
        self.volumes_info = Box()
        self.physics_info = Box()
        self.sources_info = Box()
        self.actors_info = Box()
        self.g4_verbose_level = 0
        self.g4_verbose = False
        self.g4_visualisation_flag = False

        # G4 elements and managers
        self.g4_RunManager = None
        self.volume_manager = gam.VolumeManager(self.volumes_info)
        self.g4_PhysList = None
        self.source_manager = None  # can only be created at initialisation
        self.action_manager = None
        self.g4_HepRandomEngine = None
        self.g4_vis_executive = None
        self.g4_ui_executive = None
        self.g4_ui = None

        # internal state
        self.initialized = False
        self.sim_time = None
        self.run_timing_intervals = None
        self.ui_session = None

        # default elements
        self._default_parameters()

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
            f'Geometry: {self.volumes_info}\n' \
            f'Physics: {self.physics_info}\n' \
            f'Sources: {self.sources_info}\n' \
            f'Actors: {self.actors_info}\n'
        return s

    def _default_parameters(self):
        """
        Internal. Build default elements: verbose, World, seed, physics
        """
        # G4 output
        self.set_g4_verbose(False)
        self.g4_verbose_level = 1
        # World volume
        w = self.add_volume('Box', 'World')
        w.mother = None
        m = gam.g4_units('meter')
        w.size = [3 * m, 3 * m, 3 * m]
        w.material = 'G4_AIR'
        # seed
        self.seed = 'auto'
        # physics default
        self.physics_info.name = 'QGSP_BERT_EMV'  # FIXME TO CHANGE
        # run timing
        sec = gam.g4_units('second')
        self.sim_time = 0 * sec
        self.run_timing_intervals = [[0 * sec, 1 * sec]]  # a list of begin-end time values

    @staticmethod
    def get_available_physicLists():
        # FIXME move to physics ?
        factory = g4.G4PhysListFactory()
        return factory.AvailablePhysLists()

    def dump_sources(self):
        si = self.sources_info
        s = f'Number of sources: {len(si)} '
        if self.initialized:
            s += f'(initialized)'
            s += self.source_manager.dump()
        else:
            s += f'(NOT initialized)'
            for source in si.values():
                s += gam.indent(2, f'\n{source}')
        return s

    def dump_source_types(self):
        s = f''
        for t in gam.source_builders:
            s += f'{t} '
        return s

    def dump_volumes(self, level=0):
        return self.volume_manager.dump(level)

    def dump_material_database_names(self):
        return list(self.volume_manager.material_databases.keys())

    def dump_material_database(self, db, level=0):
        if db not in self.volume_manager.material_databases:
            gam.fatal(f'Cannot find the db "{db}" in the '
                      f'list: {self.dump_material_database_names()}')
        thedb = self.volume_manager.material_databases[db]
        if db == 'NIST':
            return thedb.GetNistMaterialNames()
        return thedb.dump_materials(level)

    def dump_defined_material(self, level=0):
        if not self.initialized:
            gam.fatal(f'Cannot dump defined material before initialisation')
        return self.volume_manager.dump_defined_material(level)

    def initialize(self):
        """
        Build the main geant4 objects
        """

        if self.g4_visualisation_flag:
            log.info('Simulation: create visualisation')
            self.g4_vis_executive = g4.G4VisExecutive('warning')
            self.g4_vis_executive.Initialise()
            self.g4_ui_executive = g4.G4UIExecutive()

        log.info('Simulation: create G4RunManager')
        rm = g4.G4RunManager.GetRunManager()
        if not rm:
            rm = g4.G4RunManager()
        else:
            s = f'Cannot create a Simulation, the G4RunManager already exist.'
            gam.fatal(s)
        self.g4_RunManager = rm
        self.g4_RunManager.SetVerboseLevel(self.g4_verbose_level)

        # Cannot be initialized two times (ftm)
        if self.initialized:
            gam.fatal('Simulation already initialized. Abort')

        # check run timing
        gam.assert_run_timing(self.run_timing_intervals)

        # geometry
        log.info('Simulation: initialize Geometry')
        self.g4_RunManager.SetUserInitialization(self.volume_manager)

        # phys
        log.info('Simulation: initialize Physics')
        self.g4_PhysList = gam.create_phys_list(self.physics_info)
        self.g4_RunManager.SetUserInitialization(self.g4_PhysList)
        gam.set_cuts(self.physics_info, self.g4_PhysList)

        # sources
        log.info('Simulation: initialize Source')
        self.source_manager = gam.SourceManager(self.run_timing_intervals, self.sources_info)
        self.source_manager.initialize()

        # action
        log.info('Simulation: initialize Actions')
        self.action_manager = gam.ActionManager(self.source_manager)
        self.g4_RunManager.SetUserInitialization(self.action_manager)

        # Initialization
        log.info('Simulation: initialize G4RunManager')

        self.g4_RunManager.RunTermination()

        self.g4_RunManager.Initialize()
        self.initialized = True

        # Check overlaps
        log.info('Simulation: check volumes overlap')
        self.check_geometry_overlaps(verbose=False)

        # Actors initialization
        log.info('Simulation: initialize actors')
        self._initialize_actors()

        # visualisation
        self._initialize_visualisation()

    def g4_apply_command(self, command):
        """
        For the moment, only use it *after* runManager.Initialize
        """
        if not self.initialized:
            gam.fatal(f'Please, use g4_apply_command *after* simulation.initialize()')
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.ApplyCommand(command)

    def start(self):
        """
        Start the simulation. The runs are managed in the SourceManager.
        """
        if not self.initialized:
            gam.fatal('Use "initialize" before "start"')
        log.info('-' * 80 + '\nSimulation: START')

        # visualisation should be initialized *after* other initializations
        self._initialize_visualisation()

        start = time.time()
        self.source_manager.start(self)
        while not self.source_manager.simulation_is_terminated:
            self.source_manager.start_run()
        end = time.time()
        log.info(f'Simulation: STOP. Time = {end - start:0.1f} seconds\n' + '-' * 80)

    def set_g4_random_engine(self, engine_name, seed='auto'):
        # FIXME add more random engine later
        if engine_name != 'MersenneTwister':
            s = f'Cannot find the random engine {engine_name}\n'
            s += f'Use: MersenneTwister'
            gam.fatal(s)
        self.g4_HepRandomEngine = g4.MTwistEngine()
        g4.G4Random.setTheEngine(self.g4_HepRandomEngine)
        self.seed = seed
        if seed == 'auto':
            self.seed = random.randrange(sys.maxsize)
        g4.G4Random.setTheSeeds(self.seed, 0)

    def set_g4_verbose(self, b=True):
        self.g4_verbose = b
        if not b:
            ui = gam.UIsessionSilent()
            self.set_g4_ui_output(ui)
        else:
            self.set_g4_ui_output(None)

    def set_g4_ui_output(self, ui_session):
        # we must kept a ref to ui_session
        self.ui_session = ui_session
        # we must kept a ref to ui_manager
        self.g4_ui = g4.G4UImanager.GetUIpointer()
        self.g4_ui.SetCoutDestination(ui_session)

    def set_g4_visualisation_flag(self, b):
        if self.initialized:
            gam.fatal(f'Cannot change visualisation *after* the initialisation')
        self.g4_visualisation_flag = b

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

    def add_volume(self, solid_type, name):
        # first, create a simple Box structure
        v = self._add_element(self.volumes_info, solid_type, name)
        # then create the Volume
        # FIXME, later indicate here if several types of mage volumes are available
        if solid_type == 'Image':
            self.volume_manager.volumes[name] = gam.ImageVolume(self, v)
        else:
            self.volume_manager.volumes[name] = gam.VolumeBase(v)
        return v

    def add_source(self, source_type, name):
        s = self._add_element(self.sources_info, source_type, name)
        return s

    def add_actor(self, actor_type, name):
        # first, create a simple Box structure
        a = self._add_element(self.actors_info, actor_type, name)
        # then create the Actor
        a.g4_actor = gam.actor_build(self, a)
        return a

    def add_material_database(self, filename, name=None):
        self.volume_manager.add_material_database(filename, name)

    def _initialize_actors(self):
        for actor_info in self.actors_info.values():
            log.info(f'Init actor [{actor_info.type}] {actor_info.name}')
            # actor_info.g4_actor = gam.actor_build(actor_info) # FIXME to remove
            actor_info.g4_actor.initialize()
            gam.actor_register_actions(self, actor_info)

    def _initialize_visualisation(self):
        if not self.g4_visualisation_flag:
            return
        log.info('Simulation: initialize visualisation')
        # visualization macro
        # FIXME may be improved. Also give user options (axis etc)
        self.g4_apply_command(f'/vis/open OGLIQt')
        # self.g4_apply_command(f'/control/verbose 2')
        self.g4_apply_command(f'/vis/drawVolume')
        # self.g4_apply_command(f'/vis/viewer/flush') # not sure needed
        self.g4_apply_command(f'/tracking/storeTrajectory 1')
        self.g4_apply_command(f'/vis/scene/add/trajectories')
        self.g4_apply_command(f'/vis/scene/endOfEventAction accumulate')
        # self.uim = g4.G4UImanager.GetUIpointer()
        # self.uis = self.uim.GetG4UIWindow()
        # self.uis.GetMainWindow().setVisible(True)
        # self.uis.AddButton("my_menu", "Run", "/run/beamOn 1000")
        # self.uis.AddIcon("test", "a.xpm", "/run/beamOn 1000", "")
        # self.uis.AddMenu("test", "gam")
        # self.uis.AddButton("test", "Run", "/run/beamOn 1000")

    def prepare_for_next_run(self, sim_time, current_run_interval):
        for source_info in self.sources_info.values():
            source_info.g4_source.prepare_for_next_run(sim_time, current_run_interval)
        # print('FIXME prepare next run for geometry')
        # http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomDynamic.html
        # G4RunManager::GeometryHasBeenModified();
        # OR Rather -> Open Close geometry for all volumes for which it is required

    def check_geometry_overlaps(self, verbose=True):
        if not self.initialized:
            gam.fatal(f'Cannot check overlap: the simulation must be initialized before')
        # FIXME: later, allow to bypass this check ?
        # FIXME: How to manage the verbosity ?
        b = self.g4_verbose
        self.set_g4_verbose(verbose)
        self.volume_manager.check_overlaps()
        self.set_g4_verbose(b)
