import opengate_core as g4
from .VolumeBase import VolumeBase
from ..utility import g4_units


class HexagonVolume(VolumeBase):
    type_name = "Hexagon"

    """
    This is a special case of a polyhedra
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    """

    @staticmethod
    def set_default_user_info(user_info):
        VolumeBase.set_default_user_info(user_info)
        cm = g4_units.cm
        user_info.height = 5 * cm
        user_info.radius = 0.15 * cm

    def build_solid(self):
        u = self.user_info
        deg = g4_units.deg
        phi_start = 0 * deg
        phi_total = 360 * deg
        num_side = 6
        num_zplanes = 2
        zplane = [-u.height / 2, u.height / 2]
        radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        radius_outer = [u.radius] * num_side

        return g4.G4Polyhedra(
            u.name,
            phi_start,
            phi_total,
            num_side,
            num_zplanes,
            zplane,
            radius_inner,
            radius_outer,
        )
