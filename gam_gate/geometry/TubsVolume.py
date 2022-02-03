import gam_gate as gam
import gam_g4 as g4


class TubsVolume(gam.VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    prmin SetInnerRadius
    prmax SetOuterRadius
    pdz  SetZHalfLength
    psphi SetStartPhiAngle
    pdphi SetDeltaPhiAngle
    """

    type_name = 'Tubs'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        # default values
        u = user_info
        mm = gam.g4_units('mm')
        deg = gam.g4_units('deg')
        u.rmin = 30 * mm
        u.rmax = 40 * mm
        u.dz = 40 * mm
        u.sphi = 0 * deg
        u.dphi = 360 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Tubs(u.name, u.rmin, u.rmax, u.dz, u.sphi, u.dphi)
