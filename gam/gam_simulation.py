from gam_helpers import *
from gam_geometry import *
from gam_solid import *
from box import Box
import inspect
import logging

log = logging.getLogger(__name__)

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

    # type hint
    data_folder: str

    def __init__(self, data_folder='data/'):
        '''
        Constructor
        :param data_folder: folder where the input data of the
        simulation will be search for.
        '''
        self.data_folder = data_folder
        self.geometry = Box()

        # default world
        w = self.new_volume('world', 'Box')
        w.material = 'Air'
        w.size = [1, 1, 1]

        # default
        self.physics = {}
        self.actions = {}

    def __str__(self):
        '''
        Print a Simulation into a str
        :return: a string
        '''
        s = f'data_folder : {self.data_folder}\n'
        s += str(self.geometry)
        return s

    def initialise(self):
        '''
        Build the simulation
        '''
        print('Building simulation')

        # TODO : reset, start from scratch
        # self.__new_simulation()
        
        self.__set_geometry(self.geometry)
        self.__set_physics()
        self.__set_actions()

        print('Start ...')
        # self.run()

    def start(self):
        '''
        Start the simulation
        :return:
        '''
        self.initialise()
        print('Start ...')
        # self.run()

    def __set_geometry(self, geometry):
        print(f'Building geometry {geometry}')

        # check all volumes (avoid duplicate etc)
        check_geometry(geometry)

        # build tree
        self.tree = create_geometry_tree(geometry)
        s = pretty_print_tree(self.tree, geometry)
        print(s)

        # build the volumes in the tree order
        for v in self.tree:
            # self.__build_volume(geometry[v])  FIXME 
            build_volume_VERSION1(geometry[v])


    def __build_volume(self, vol):
        if vol.type not in g_solid_builders:
            s = f"The volume type '{vol.type}' is unknown"
            raise_except(s)
        builder = g_solid_builders[vol.type]
        builder(vol)


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


    def __set_physics(self):
        print('physics')

    def __set_actions(self):
        print('actions')



