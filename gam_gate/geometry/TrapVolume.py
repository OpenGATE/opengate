import gam_gate as gam
import gam_g4 as g4


class TrapVolume(gam.VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    dx1 Half x length of the side at y=-pdy1 of the face at -pdz
    dx2 Half x length of the side at y=+pdy1 of the face at -pdz
    dz Half z length
    theta Polar angle of the line joining the centres of the faces at -/+pdz
    phi Azimuthal angle of the line joining the centre of the face at -pdz to the centre of the face at +pdz
    dy1 Half y length at -pdz
    dy2 Half y length at +pdz
    dx3 Half x length of the side at y=-pdy2 of the face at +pdz
    dx4 Half x length of the side at y=+pdy2 of the face at +pdz
    alp1 Angle with respect to the y axis from the centre of the side (lower endcap)
    alp2 Angle with respect to the y axis from the centre of the side (upper endcap)
    """

    type_name = 'Trap'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        u = user_info
        mm = gam.g4_units('mm')
        u.dx1 = 30 * mm
        u.dx2 = 40 * mm
        u.dy1 = 40 * mm
        u.dx3 = 10 * mm
        u.dx4 = 14 * mm
        u.dy2 = 16 * mm
        u.dz = 60 * mm
        deg = gam.g4_units('deg')
        u.theta = 20 * deg
        u.phi = 5 * deg
        u.alp1 = u.alp2 = 10 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Trap(u.name,
                         u.dz, u.theta, u.phi, u.dy1,
                         u.dx1, u.dx2, u.alp1, u.dy2,
                         u.dx3, u.dx4, u.alp2)
