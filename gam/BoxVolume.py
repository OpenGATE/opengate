import gam
import gam_g4 as g4


class BoxVolume(gam.VolumeBase):

    volume_type = 'Box'

    def __init__(self, name):
        gam.VolumeBase.__init__(self, self.volume_type, name)
        # default values
        cm = gam.g4_units('cm')
        self.user_info.size = 10 * cm

    def build_solid(self):
        u = self.user_info
        return g4.G4Box(u.name,
                        u.size[0] / 2.0,
                        u.size[1] / 2.0,
                        u.size[2] / 2.0)
