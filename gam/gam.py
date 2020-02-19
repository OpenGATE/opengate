from gam_helpers import *
from box import Box
import inspect
import logging

log = logging.getLogger(__name__)

def fatal(s):
    log.fatal(s)
    exit()

class Simulation:
    """
    this is a simulation
    """
    data_folder: str

    def __init__(self, data_folder='None'):
        '''
        Constructor
        :param data_folder: folder where the input data of the
        simulation will be search for        
        '''
        self.data_folder = data_folder
        self.geometry = Box()
        self.geometry.world = Box()
        w = self.geometry.world
        w.name = 'world'
        w.type = 'Box'
        w.material = 'Air'
        w.size = [1, 1, 1]
        self.physics = {}
        self.actions = {}
        print('init')

    def __str__(self):
        '''
        To print a Simulation
        :return: a string
        '''
        s = f'data_folder : {self.data_folder}\n'
        s += str(self.geometry)
        return s

    def start(self):
        '''
        Build and start the simulation
        :return:
        '''
        print('Building simulation')
        self.__set_geometry(self.geometry)
        self.__set_physics()
        self.__set_actions()
        print('Start ...')
        # self.run()

    def __set_geometry(self, geometry):
        print('Building geometry', geometry)

        # build tree
        self.tree = create_geometry_tree(geometry)
        print(self.tree)

        # print tree
        for pre, fill, node in RenderTree(self.tree['world']):
            print("%s%s" % (pre, node.name))

        # build the world
        self.__build_volume(geometry.world)
        # self.__build_volume(vol)

        exit()

        # build all volume
        for v in geometry:
            if v == 'world':
                # already done
                continue
            vol = geometry[v]
            self.__build_volume(vol)
            name = vol.name #may fail here (no name or already exist)
            p = self.tree[vol.mother] #may fail here (no parent exist)
            v = Node(name, parent=p)
            self.tree[name] = v

        # print tree
        for pre, fill, node in RenderTree(w):
            print("%s%s" % (pre, node.name))

    def __build_volume(self, vol):
        print('build ---->', vol)
        try:
            print('build volume', vol.name, vol.type)
            builder = volume_builders[vol.type]
            builder(vol)
        except:
            print('ERROR in build_volume', vol)
            exit()

    def new_volume(self, name, volume_type):
        # check if name is unique
        if name in self.geometry:
            raise_except(f'A volume with the name {name} already exist.')
        
        v = Box()
        v.mother = 'world'
        v.type = volume_type
        # get default values ?
        #v.merge_update(get_args_from_box())
        v.name = name
        self.geometry[name] = v
        print('new volume',v)
        return v


    def set_geometry_world(self, world):
        print('Building world')
        # check material + size
        # G4 build the world, need size + material

    def __set_physics(self):
        print('physics')

    def __set_actions(self):
        print('actions')



def get_args_from_box():
    a = inspect.signature(fake_G4Box)
    print(a)
    print(type(a))
    return a.parameters


def fake_box_builder(**kwargs):
    print('Fake_box_builder')
    print('Box name', kwargs['name'])
    print('kwargs = ', kwargs)

    # extract needed parameters ?
    a = inspect.signature(fake_G4Box)
    for p in a._parameters:
        print(p)

    try:
        v = fake_g4box(**kwargs)
    except:
        print('ERROR, require x_half_length etc')
        print(inspect.signature(fake_g4box))
        exit()
    return 'volume'


def G4Box_builder(v):
    if 'size' not in v:
        try:
            for i in range(3):
                v.size[i] = v.half_size[i]*2
        except:
            print('ERROR, cannot find half_size')
    else:
        # size takes prior to half_size
        if 'half_size' in v:
            print('Warning recompute half_size from size')
        try:
            v.half_size = [0,0,0]
            for i in range(3):
                v.half_size[i] = v.size[i]/2.0
        except:
            print('ERROR, cannot find size', v)
            exit()
    hx = v.half_size[0]
    hy = v.half_size[1]
    hz = v.half_size[2]
    return fake_G4Box(v.name, hx, hy, hz)


def fake_G4Box(name, x_half_length, y_half_length, z_half_length):
    # def fake_G4Box(pName, pX, pY, pZ):
    print('G4Box, ', name, x_half_length, y_half_length, z_half_length)
    return 'volume_constructed'


volume_builders = {}
volume_builders['Box'] = G4Box_builder


def make_a_volume(typename, params):
    # param is a box

    # build solid
    # v = g4.G4Box(name, x_half_length, y_half_length, z_half_length)
    builder = volume_builders[typename]
    v = builder(**params)
    print(v)

    # build logical volume
    # get material
    #try:
    #    params.material
    # log = g4.G4LogicalVolume(v, material, 'log_'+name)

    # build associated region (for cuts)

    # set sensitivity detector callback ?

    # set vis attribute

    # retrieve mother volume
    # mother_log = get_logical_volume(mother)

    # build physical volume
    '''
    phys = g4.G4PVPlacement(newRotationMatrix,        # rotation with respect to its mother volume
                            position,                 # translation with respect to its mother volume
                            log,                      # the associated logical volume
                            'phys_'+name,             # physical volume name
                            mother_log,               # the mother logical volume
                            false,                    # for future use,, can be set to false
                            copyNumber,               # copy number
                            false)                    # false/true = no/yes overlap check triggered
    '''

    return v
