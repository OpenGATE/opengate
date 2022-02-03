import gam_gate as gam
import gam_g4 as g4
import math


class SphereVolume(gam.VolumeBase):
    type_name = 'Sphere'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        user_info.rmin = 0
        user_info.rmax = 1
        user_info.sphi = 0
        user_info.dphi = 2 * math.pi
        user_info.stheta = 0
        user_info.dtheta = math.pi

    def build_solid(self):
        u = self.user_info
        return g4.G4Sphere(u.name,
                           u.rmin, u.rmax, u.sphi, u.dphi,
                           u.stheta, u.dtheta)
