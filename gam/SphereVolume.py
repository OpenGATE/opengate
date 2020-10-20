import gam
import gam_g4 as g4
import math


class SphereVolume(gam.VolumeBase):

    volume_type = 'Sphere'

    def __init__(self, name):
        gam.VolumeBase.__init__(self, self.volume_type, name)
        u = self.user_info
        u.Rmin = 0
        u.Rmax = 1
        u.SPhi = 0
        u.DPhi = 2 * math.pi
        u.STheta = 0
        u.DTheta = math.pi

    def build_solid(self):
        u = self.user_info
        return g4.G4Sphere(u.name,
                           u.Rmin, u.Rmax, u.SPhi, u.DPhi,
                           u.STheta, u.DTheta)
