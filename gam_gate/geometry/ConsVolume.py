import gam_gate as gam
import gam_g4 as g4


class ConsVolume(gam.VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    """

    type_name = 'Cons'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        # default values
        u = user_info
        mm = gam.g4_units('mm')
        deg = gam.g4_units('deg')
        u.rmin1 = 5 * mm
        u.rmax1 = 10 * mm
        u.rmin2 = 20 * mm
        u.rmax2 = 25 * mm
        u.dz = 40 * mm
        u.sphi = 0 * deg
        u.dphi = 45 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Cons(u.name, u.rmin1, u.rmax1, u.rmin2, u.rmax2, u.dz, u.sphi, u.dphi)
