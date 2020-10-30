import gam
import gam_g4 as g4
import numpy as np
from scipy.spatial.transform import Rotation


def get_source_position(type_name):
    return gam.new_element('SourcePosition', type_name).user_info


"""
    source = sim.add_source('GenericSource', 'my_source')    
    
    (1)
    Special case with direct G4 SPS object
    source.position = gam.get_source_position('G4SPSPosDistribution')
    g = source.position.object
    g.SetPosDisType('Volume')
    p.SetPosDisShape('Sphere')
    etc --> see G4 file G4SPSPosDistribution

    (2) 
    point     : center
    box       : center, size, rotation
    disc      : center, radius, rotation
    sphere    : center, radius --> special case of ellipse
    ellipsoid : center, rotation, radius (3D) 
    cylinder  : center, radius, rotation, length
    
    (3) Later
    - confined with volume

"""


class SourcePositionBase(gam.ElementBase):
    type_name = 'G4SPSPosDistribution'

    def __init__(self, name):
        gam.ElementBase.__init__(self, name)
        self.generator = g4.G4SPSPosDistribution()
        self.rndm = g4.G4SPSRandomGenerator()
        self.generator.SetBiasRndm(self.rndm)

    def initialize(self):
        gam.ElementBase.initialize(self)
        # self.generator.SetVerbosity(10)

    def shoot(self):
        return self.generator.GenerateOne()


# http://extremelearning.com.au/how-to-generate-uniformly-random-points-on-n-spheres-and-n-balls/

# G4SPSPosDistribution ?

class SourcePositionDisc(SourcePositionBase):
    type_name = 'disc'

    def __init__(self, name):
        SourcePositionBase.__init__(self, name)
        cm = gam.g4_units('cm')
        self.user_info.center = [0, 0, 0]
        self.user_info.radius = 1 * cm
        self.user_info.rotation = Rotation.identity().as_matrix()
        self.rot = None

    def initialize(self):
        SourcePositionBase.initialize(self)
        self.rot = Rotation.from_matrix(self.user_info.rotation)

    def shoot(self):
        # https://stats.stackexchange.com/questions/120527/simulate-a-uniform-distribution-on-a-disc
        # FIXME later --> generate by batch? maybe gain time?
        c = self.user_info.center
        radius = self.user_info.radius
        rho = g4.G4UniformRand() * radius
        theta = g4.G4UniformRand() * 2 * np.pi
        p = [rho * np.cos(theta), rho * np.sin(theta), 0]
        p = self.rot.apply(p) + c
        return gam.vec_np_as_g4(p)


class SourcePositionSphere(SourcePositionBase):
    type_name = 'sphere'

    def __init__(self, name):
        SourcePositionBase.__init__(self, name)
        cm = gam.g4_units('cm')
        self.user_info.center = [0, 0, 0]
        self.user_info.radius = 1 * cm
        self.r2 = 0.0
        self.diameter = 0.0

    def initialize(self):
        self.r2 = self.user_info.radius * self.user_info.radius
        self.diameter = 2 * self.user_info.radius

    def shoot(self):
        # random by rejection
        norm = 2 * self.r2
        while norm > self.r2:
            p = np.array([g4.G4UniformRand(), g4.G4UniformRand(), g4.G4UniformRand()])
            # print('p', p)
            p = p * self.diameter - self.user_info.radius
            # print('p', p)
            norm = p.dot(p)
            # print('norm', norm)
        p = p + self.user_info.center
        return gam.vec_np_as_g4(p)
