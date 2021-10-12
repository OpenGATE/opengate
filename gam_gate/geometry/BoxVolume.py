import gam_gate as gam
import gam_g4 as g4


class BoxVolume(gam.VolumeBase):
    type_name = 'Box'

    @staticmethod
    def set_default_user_info(user_info):
        gam.VolumeBase.set_default_user_info(user_info)
        cm = gam.g4_units('cm')
        user_info.size = [10 * cm, 10 * cm, 10 * cm]

    def build_solid(self):
        u = self.user_info
        return g4.G4Box(u.name,
                        u.size[0] / 2.0,
                        u.size[1] / 2.0,
                        u.size[2] / 2.0)
