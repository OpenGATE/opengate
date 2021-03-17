import gam
import gam_g4 as g4


class TubsVolume(gam.VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    pRMin SetInnerRadius
    pRMax SetOuterRadius
    pDz  SetZHalfLength
    pSPhi SetStartPhiAngle
    pDPhi SetDeltaPhiAngle
    """

    type_name = 'Tubs'

    def __init__(self, name):
        gam.VolumeBase.__init__(self, name)
        # default values
        u = self.user_info
        mm = gam.g4_units('mm')
        deg = gam.g4_units('deg')
        u.RMin = 30 * mm
        u.RMax = 40 * mm
        u.Dz = 40 * mm
        u.SPhi = 0 * deg
        u.DPhi = 360 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Tubs(u.name, u.RMin, u.RMax, u.Dz, u.SPhi, u.DPhi)
