from box import Box
import gam_gate as gam
import gam_g4 as g4
import sys


def create_phys_list(physics):
    # set physics list
    factory = g4.G4PhysListFactory()
    phys_list = factory.GetReferencePhysList(physics.physics_list_name)
    # FIXME check if exist
    # FIXME EM only PL to create
    return phys_list


def set_cuts(physics, g4_PhysList):
    # set cuts
    # g4_PhysList.DumpList()
    # g4_PhysList.DumpCutValuesTable(1)
    print('default cut value', g4_PhysList.GetDefaultCutValue())
    pct = g4.G4ProductionCutsTable.GetProductionCutsTable()
    # print('pct', pct)
    eV = gam.g4_units('eV')
    GeV = gam.g4_units('GeV')
    pct.SetEnergyRange(250 * eV, 100 * GeV)
    # print('default cut value', g4_PhysList.GetDefaultCutValue())


""" 
    The following functions are a mechanism to automatically create G4VModularPhysicsList
    from simple G4VPhysicsConstructor. 

    Current available lists:
    G4EmStandardPhysics_option1
    G4EmStandardPhysics_option2
    G4EmStandardPhysics_option3
    G4EmStandardPhysics_option4

--> Example of dynamically created class:
class G4EmStandardPhysics_option1(g4.G4VModularPhysicsList):
    def __init__(self):
        g4.G4VModularPhysicsList.__init__(self)
        self.p = g4.G4EmStandardPhysics_option1(1)
        self.RegisterPhysics(self.p)
"""

# Names of the PL that can be created dynamically
available_additional_physics_lists = [
    'G4EmStandardPhysics_option1',
    'G4EmStandardPhysics_option2',
    'G4EmStandardPhysics_option3',
    'G4EmStandardPhysics_option4',
    'G4EmStandardPhysicsGS',
    'G4EmLowEPPhysics',
    'G4EmLivermorePhysics',
    'G4EmLivermorePolarizedPhysics',
    'G4EmPenelopePhysics',
    'G4EmDNAPhysics',
    'G4OpticalPhysics'
]


def create_modular_physics_list_class(pl_class):
    """
    Create a class (not on object!) which:
    - inherit from g4.G4VModularPhysicsList
    - register a single G4 PhysicList (G4VPhysicsConstructor)
    - is named with the name of this PhysicList
    """
    # get the name of the G4 PhysicList
    name = pl_class.__name__
    # create the class with constructor
    the_class = type(name,
                     (g4.G4VModularPhysicsList,),
                     {'pl_class': pl_class,
                      '__init__': modular_physics_list_constructor,
                      '__del__': modular_physics_list_destructor})
    return the_class


def modular_physics_list_constructor(self):
    """
    Constructor of the above, dynamically created class.
    - call the constructor of the super class (G4VModularPhysicsList)
    - Create and register the physic list (G4VPhysicsConstructor)
    """
    g4.G4VModularPhysicsList.__init__(self)
    self.p = self.pl_class(1)
    self.RegisterPhysics(self.p)


def modular_physics_list_destructor(self):
    """
    For debug
    """
    pass


def create_modular_physics_list(pl_name):
    """
    Dynamically create a class with the given PhysicList
    Only possible if the class exist in g4
    """
    # Retrieve the G4VPhysicsConstructor class
    try:
        a = getattr(sys.modules['gam_g4'], pl_name)
    except:
        s = f'Cannot find the class {pl_name} in gam_g4'
        gam.fatal(s)
    # Create the class
    b = gam.create_modular_physics_list_class(a)
    # Create the object
    return b()
