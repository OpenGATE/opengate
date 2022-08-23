import opengate as gate
import opengate_core as g4


class BoxVolume(gate.VolumeBase):
    type_name = "Box"

    @staticmethod
    def set_default_user_info(user_info):
        gate.VolumeBase.set_default_user_info(user_info)
        cm = gate.g4_units("cm")
        user_info.size = [10 * cm, 10 * cm, 10 * cm]

    def build_solid(self):
        u = self.user_info
        return g4.G4Box(u.name, u.size[0] / 2.0, u.size[1] / 2.0, u.size[2] / 2.0)
