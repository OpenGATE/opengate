import gam
import gam_g4 as g4


class TrapVolume(gam.VolumeBase):
    """
    http://geant4-userdoc.web.cern.ch/geant4-userdoc/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html
    pDx1 Half x length of the side at y=-pDy1 of the face at -pDz
    pDx2 Half x length of the side at y=+pDy1 of the face at -pDz
    pDz Half z length
    pTheta Polar angle of the line joining the centres of the faces at -/+pDz
    pPhi Azimuthal angle of the line joining the centre of the face at -pDz to the centre of the face at +pDz
    pDy1 Half y length at -pDz
    pDy2 Half y length at +pDz
    pDx3 Half x length of the side at y=-pDy2 of the face at +pDz
    pDx4 Half x length of the side at y=+pDy2 of the face at +pDz
    pAlp1 Angle with respect to the y axis from the centre of the side (lower endcap)
    pAlp2 Angle with respect to the y axis from the centre of the side (upper endcap)
    """

    type_name = 'Trap'

    def __init__(self, name):
        gam.VolumeBase.__init__(self, name)
        # default values
        u = self.user_info
        mm = gam.g4_units('mm')
        u.Dx1 = 30 * mm
        u.Dx2 = 40 * mm
        u.Dy1 = 40 * mm
        u.Dx3 = 10 * mm
        u.Dx4 = 14 * mm
        u.Dy2 = 16 * mm
        u.Dz = 60 * mm
        deg = gam.g4_units('deg')
        u.Theta = 20 * deg
        u.Phi = 5 * deg
        u.Alp1 = u.Alp2 = 10 * deg

    def build_solid(self):
        u = self.user_info
        return g4.G4Trap(u.name,
                         u.Dz, u.Theta, u.Phi, u.Dy1,
                         u.Dx1, u.Dx2, u.Alp1, u.Dy2,
                         u.Dx3, u.Dx4, u.Alp2)
