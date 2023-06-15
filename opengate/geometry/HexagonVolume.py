import opengate as gate
import opengate_core as g4


class HexagonVolume(gate.VolumeBase):
    type_name = "Hexagon"

    user_info_defaults = {}
    user_info_defaults["height"] = (
        5 * gate.g4_units("cm"),
        {"doc": "Height of the hexagon volume."},
    )
    user_info_defaults["radius"] = (
        0.15 * gate.g4_units("cm"),
        {"doc": "Radius from the center to corners."},
    )
    """
    This is a special case of a polyhedra
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_solid(self):
        deg = gate.g4_units("deg")
        phi_start = 0 * deg
        phi_total = 360 * deg
        num_side = 6
        num_zplanes = 2
        zplane = [-self.height / 2, self.height / 2]
        radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        radius_outer = [self.radius] * num_side

        return g4.G4Polyhedra(
            self.name,
            phi_start,
            phi_total,
            num_side,
            num_zplanes,
            zplane,
            radius_inner,
            radius_outer,
        )
