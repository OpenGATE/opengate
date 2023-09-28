import opengate_core as g4
from .VolumeBase import VolumeBase
from ..utility import g4_units


class TubsVolume(VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    prmin SetInnerRadius
    prmax SetOuterRadius
    pdz  SetZHalfLength
    psphi SetStartPhiAngle
    pdphi SetDeltaPhiAngle
    """

    type_name = "Tubs"

    @staticmethod
    def set_default_user_info(user_info):
        VolumeBase.set_default_user_info(user_info)
        # default values
        u = user_info
        mm = g4_units.mm
        deg = g4_units.deg
        u.rmin = 30 * mm
        u.rmax = 40 * mm
        u.dz = (
            40 * mm
        )  # Half-length in Z, while in previous Gate, the cylinder was total length (not half)
        u.sphi = 0 * deg
        u.dphi = 360 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Tubs(u.name, u.rmin, u.rmax, u.dz, u.sphi, u.dphi)
