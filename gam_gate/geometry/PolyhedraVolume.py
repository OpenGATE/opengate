import gam_gate as gam
import gam_g4 as g4


class PolyhedraVolume(gam.VolumeBase):
    type_name = 'Polyhedra'

    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    """

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        cm = gam.g4_units('cm')
        deg = gam.g4_units('deg')
        user_info.phi_start = 0 * deg
        user_info.phi_total = 360 * deg
        user_info.num_side = 6
        user_info.num_zplanes = 2
        h = 5 * cm
        user_info.zplane = [-h / 2, h - h / 2]
        user_info.radius_inner = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        user_info.radius_outer = [0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm, 0.15 * cm]

    def build_solid(self):
        u = self.user_info
        return g4.G4Polyhedra(u.name,
                              u.phi_start, u.phi_total,
                              u.num_side, u.num_zplanes,
                              u.zplane, u.radius_inner, u.radius_outer)
