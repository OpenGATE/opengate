import gam
import gam_g4 as g4
import numpy as np
from scipy.spatial.transform import Rotation


def get_source_direction(type_name):
    return gam.new_element('SourceDirection', type_name).user_info


"""
    source = sim.add_source('GenericSource', 'my_source')    
    
    (1)
    Special case with direct G4 SPS object
    source.direction = gam.get_source_direction('G4SPSAngDistribution')
    g = source.direction.object
    g.SetMinTheta(np.pi/3s)
    p.SetMinTheta(np.pi/2)
    etc ... --> see G4 file G4SPSAngDistribution

    (2) See helpers_sources.py for the list of direction types 
    

"""


class SourceDirectionBase(gam.ElementBase):
    type_name = 'G4SPSAngDistribution'

    def __init__(self, name):
        gam.ElementBase.__init__(self, name)
        self.generator = g4.G4SPSAngDistribution()
        self.rndm = g4.G4SPSRandomGenerator()
        self.generator.SetBiasRndm(self.rndm)

    def initialize(self):
        gam.ElementBase.initialize(self)
        # self.generator.SetVerbosity(10)

    def shoot(self):
        return self.generator.GenerateOne()


