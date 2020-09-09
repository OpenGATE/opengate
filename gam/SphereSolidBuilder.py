import gam
import gam_g4 as g4
import math


class SphereSolidBuilder(gam.SolidBuilderBase):

    def init_user_info(self, user_info):
        user_info.Rmin = 0
        user_info.Rmax = 1
        user_info.SPhi = 0
        user_info.DPhi = 2 * math.pi
        user_info.STheta = 0
        user_info.DTheta = math.pi

    def Build(self, user_info):
        u = user_info
        return g4.G4Sphere(user_info.name,
                           u.Rmin, u.Rmax, u.SPhi, u.DPhi,
                           u.STheta, u.DTheta)
