import opengate_core as g4
from .VolumeBase import VolumeBase
from ..utility import g4_units


class TrdVolume(VolumeBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=g4trd

    dx1 Half-length along X at the surface positioned at -dz
    dx2 Half-length along X at the surface positioned at +dz
    dy1 Half-length along Y at the surface positioned at -dz
    dy2 Half-length along Y at the surface positioned at +dz
    zdz Half-length along Z axis

    """

    type_name = "Trd"

    @staticmethod
    def set_default_user_info(user_info):
        VolumeBase.set_default_user_info(user_info)
        u = user_info
        mm = g4_units.mm
        u.dx1 = 30 * mm
        u.dx2 = 10 * mm
        u.dy1 = 40 * mm
        u.dy2 = 15 * mm
        u.dz = 60 * mm

    def build_solid(self):
        u = self.user_info
        return g4.G4Trd(u.name, u.dx1, u.dx2, u.dy1, u.dy2, u.dz)
