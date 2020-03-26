
from .gam_geometry import *
from box import Box

class Simulation:
    '''
    This class describes a complete simulation with several parts:
    - geometry
    - physics
    - sources
    - scorers
    - timing information (FIXME)
    - run
    '''

    def __init__(self, data_folder='data/'):
        '''
        Constructor
        :param data_folder: folder where the input data of the
        simulation will be search for.
        '''
        self.data_folder = data_folder
        self.material_files = []
        self.geometry = Box() # array ?

        # default world
        w = self.new_volume('world', 'Box')
        w.material = 'Air'
        w.size = [1, 1, 1]

        # default
        #self.physics = Box()
        #self.source = Box() # array ?
        #self.scorer = Box() # array ?

        #
        self.initialized = False

    def __str__(self):
        '''
        Print a Simulation
        :return: a string
        '''
        s = f'data_folder : {self.data_folder}\n'
        s += f'geometry : {str(self.geometry)}\n'
        #s += f'physics : {str(self.physics)}\n'
        #s += f'source : {str(self.source)}\n'
        #s += f'scorer : {str(self.scorer)}\n'
        return s

    def initialise(self):
        '''
        Build the simulation
        '''
        print('Initialize simulation')

        # TODO : reset, start from scratch
        if self.initialized == True:
            print('Already initialized. Abort')
            exit(0)

        self.geometry_tree = geometry_initialize(self.geometry)
        #self.__initialize_geometry()
        #self.__initialize_physics()
        #self.__initialize_source()
        #self.__initialize_scorer()

        self.initialized = True

    def start(self, nb_events):
        '''
        Start the simulation
        '''
        self.initialise()
        print('Start ...', nb_events)
        # self.run()

    def new_volume(self, name, volume_type):
        # check if name is unique
        if name in self.geometry:
            raise_except(f'A volume with the name {name} already exist.')
        v = Box()
        v.mother = 'world'
        v.type = volume_type
        v.name = name
        self.geometry[name] = v
        return v

    def set_physics_list(self, name):
        #print('physics', name)
        return Box()

    def new_source(self, name, source_type):
        #print('source', name, source_type)
        return Box()

    def new_scorer(self, name, scorer_type):
        #print('scorer',name, scorer_type)
        return Box()

    def add_material_file(self, filename):
        self.material_files.append(filename)

