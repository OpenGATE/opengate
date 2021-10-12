import gam_gate as gam
import gam_g4 as g4
import math


class SphereVolume(gam.VolumeBase):
    type_name = 'Sphere'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        user_info.Rmin = 0
        user_info.Rmax = 1
        user_info.SPhi = 0
        user_info.DPhi = 2 * math.pi
        user_info.STheta = 0
        user_info.DTheta = math.pi

    def build_solid(self):
        u = self.user_info
        return g4.G4Sphere(u.name,
                           u.Rmin, u.Rmax, u.SPhi, u.DPhi,
                           u.STheta, u.DTheta)
