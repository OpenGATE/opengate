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
        u.Rmin1 = 5 * mm
        u.Rmax1 = 10 * mm
        u.Rmin2 = 20 * mm
        u.Rmax2 = 25 * mm
        u.Dz = 40 * mm
        u.SPhi = 0 * deg
        u.DPhi = 45 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Cons(u.name, u.Rmin1, u.Rmax1, u.Rmin2, u.Rmax2, u.Dz, u.SPhi, u.DPhi)
