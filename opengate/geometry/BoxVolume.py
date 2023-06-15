import opengate as gate
import opengate_core as g4


class BoxVolume(gate.VolumeBase):
    user_info_defaults = {}
    user_info_defaults["size"] = (
        [10 * gate.g4_units("cm"), 10 * gate.g4_units("cm"), 10 * gate.g4_units("cm")],
        {"doc": "3 component list of side lengths of the box."},
    )

    type_name = "Box"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_solid(self):
        return g4.G4Box(
            self.name, self.size[0] / 2.0, self.size[1] / 2.0, self.size[2] / 2.0
        )
