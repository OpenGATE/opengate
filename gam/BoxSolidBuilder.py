import gam
import gam_g4 as g4


class BoxSolidBuilder(gam.SolidBuilderBase):

    def init_user_info(self, user_info):
        cm = gam.g4_units('cm')
        user_info.size = 10*cm

    def Build(self, user_info):
        return g4.G4Box(user_info.name,
                        user_info.size[0] / 2.0,
                        user_info.size[1] / 2.0,
                        user_info.size[2] / 2.0)
