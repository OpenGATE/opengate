import opengate as gate
import opengate_core as g4
from box import Box
from scipy.spatial.transform import Rotation
import numpy as np


class RepeatParametrisedVolume(gate.VolumeBase):
    """
    Allow to repeat a volume with translations
    """

    user_info_defaults = {}
    user_info_defaults["linear_repeat"] = (
        None,
        {"required": True},
    )
    user_info_defaults["offset"] = (
        [0, 0, 0],
        {"doc": "3 component vector or list."},
    )
    user_info_defaults["start"] = ("auto", {})
    user_info_defaults["offset_nb"] = (1, {})

    type_name = "RepeatParametrised"

    def __init__(self, repeated_volume, *args, **kwargs):
        if not "name" in kwargs:
            kwargs["name"] = f"{repeated_volume.name}_param"
        super().__init__(*args, **kwargs)
        if repeated_volume.build_physical_volume is True:
            gate.warning(
                f"The repeated volume {repeated_volume.name} must have the "
                "'build_physical_volume' option set to False."
                "Setting it to False."
            )
            repeated_volume.build_physical_volume = False
        self.repeated_volume = repeated_volume
        if self.start is None:
            self.start = [
                -(x - 1) * y / 2.0 for x, y in zip(self.linear_repeat, self.translation)
            ]

    def construct_solid(self):
        # no solid to build
        pass

    def construct_logical_volume(self):
        # make sure the repeated volume's logical volume is constructed
        if self.repeated_volume.g4_logical_volume is None:
            self.repeated_volume.construct_logical_volume()
        # set log vol
        self.g4_logical_volume = self.repeated_volume.g4_logical_volume

    def create_repeat_parametrisation(self):
        # create parameterised
        keys = [
            "linear_repeat",
            "start",
            "translation",
            "rotation",
            "offset",
            "offset_nb",
        ]
        p = {}
        for k in keys:
            p[k] = self.user_info[k]
        self.param = g4.GateRepeatParameterisation()
        self.param.SetUserInfo(p)

    def construct_physical_volume(self):
        # find the mother's logical volume
        st = g4.G4LogicalVolumeStore.GetInstance()
        g4_mother_logical_volume = st.GetVolume(self.mother, False)
        if not g4_mother_logical_volume:
            gate.fatal(f"The mother of {self.name} cannot be the world.")

        self.create_repeat_parametrisation()

        # number of copies
        n = (
            self.param.linear_repeat[0]
            * self.param.linear_repeat[1]
            * self.param.linear_repeat[2]
            * self.param.offset_nb
        )

        # (only daughter)
        # g4.EAxis.kUndefined => faster
        self.g4_physical_volumes.append(
            g4.G4PVParameterised(
                self.name,
                self.g4_logical_volume,
                g4_mother_logical_volume,
                g4.EAxis.kUndefined,
                n,
                self.param,
                False,
            )
        )
