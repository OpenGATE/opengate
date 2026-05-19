from .base import SourceBase
import opengate_core as g4
from .generic import GenericSource
from box import Box
from ..base import UserInfoValidatorBase
from ..base import process_cls
from ..exception import fatal, warning
import numpy as np
from ..logger import logger
import os


def _wts_direction_parameters():
    return Box(
        {
            "a1": [],
            "a2": [],
            "b1": [],
            "b2": [],
            "plane_distance": [],
            "plane_phi": [],
            "init_sampling_count": 1000000,
            "init_number_of_threads": 0,
            "act_ratio": [],
            "max_solid_angle": [],
            "skip_mode": False,
        }
    )


class WTSDirectionValidator(UserInfoValidatorBase):
    """Validates the 'direction' Box."""

    __schema__ = set(_wts_direction_parameters().keys())

    def set_simulation(self, simulation):
        self.simulation = simulation

    def is_integer(self, val):
        return isinstance(val, (int, np.integer))

    def is_numeric(self, val):
        return isinstance(val, (int, float, np.number))

    def validate_attr_against_nti(self, b, attr_name):
        attr = b[attr_name]
        if isinstance(attr, list):
            if len(attr) != self.num_intervals and len(attr) != 1:
                fatal(
                    f"'{self.context_name}.{attr_name}' must be a list of length 1 or {self.num_intervals} (number of timing intervals)."
                )
            for i, v in enumerate(attr):
                if not self.is_numeric(v):
                    fatal(
                        f"All elements of '{self.context_name}.{attr_name}' must be numbers."
                    )
                    b[attr_name][i] = float(v)
        elif self.is_numeric(attr):
            logger.info(
                f"'{self.context_name}.{attr_name}' is converted to a list of length 1."
            )
            b[attr_name] = [float(attr)]
        else:
            fatal(
                f"'{self.context_name}.{attr_name}' must be a number or a list of numbers."
            )

    def get_attr_interval(self, b, attr_name, interval_index):
        attr = b[attr_name]
        if len(attr) == 1:
            return attr[0]
        else:
            return attr[interval_index]

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        self.context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        nti_sized_attrs = [
            "a1",
            "a2",
            "b1",
            "b2",
            "act_ratio",
            "max_solid_angle",
            "plane_distance",
            "plane_phi",
        ]
        for attr in nti_sized_attrs:
            self.validate_attr_against_nti(b, attr)
        self.num_intervals = len(self.simulation.run_timing_intervals)
        for int_idx in range(self.num_intervals):
            a1 = self.get_attr_interval(b, "a1", int_idx)
            a2 = self.get_attr_interval(b, "a2", int_idx)
            if a1 >= a2:
                fatal(
                    f"'a1' must be less than 'a2' for timing interval {int_idx} in '{self.context_name}'."
                )
            b1 = self.get_attr_interval(b, "b1", int_idx)
            b2 = self.get_attr_interval(b, "b2", int_idx)
            if b1 >= b2:
                fatal(
                    f"'b1' must be less than 'b2' for timing interval {int_idx} in '{self.context_name}'."
                )
            max_solid_angle = self.get_attr_interval(b, "max_solid_angle", int_idx)
            if max_solid_angle <= 0 or max_solid_angle > 2 * np.pi:
                fatal(
                    f"'max_solid_angle' must be in the range (0, 2*pi] for timing interval {int_idx} in '{self.context_name}'."
                )
            act_ratio = self.get_attr_interval(b, "act_ratio", int_idx)
            if act_ratio < 0 or act_ratio > 1:
                fatal(
                    f"'act_ratio' must be in the range [0, 1] for timing interval {int_idx} in '{self.context_name}'."
                )
            plane_distance = self.get_attr_interval(b, "plane_distance", int_idx)
            if plane_distance <= 0:
                fatal(f"'plane_distance' must be positive in '{self.context_name}'.")
            plane_phi = self.get_attr_interval(b, "plane_phi", int_idx)
            if plane_phi < 0 or plane_phi >= np.pi * 2:
                fatal(
                    f"'plane_phi' must be in the range [0, np.pi * 2) in '{self.context_name}'."
                )
        if not self.is_integer(b.init_sampling_count) or b.init_sampling_count <= 0:
            fatal(f"'init_sampling_count' must be positive in '{self.context_name}'.")

        if b.init_number_of_threads == 0:
            b.init_number_of_threads = self.simulation.number_of_threads
            logger.info(
                f"'init_number_of_threads' is set to the number of CPU cores: {b.init_number_of_threads}."
            )

        if (
            not self.is_integer(b.init_number_of_threads)
            or b.init_number_of_threads < 0
            or b.init_number_of_threads > os.cpu_count()
        ):
            warning(
                f"'init_number_of_threads' must be a positive integer less than or equal to the number of CPU cores. Setting it to {os.cpu_count()}."
            )

        if not isinstance(b.skip_mode, bool):
            fatal(f"'skip_mode' must be a boolean in '{self.context_name}'.")


class WindowTurboSource(GenericSource, g4.GateWindowTurboSource):
    direction: Box

    user_info_defaults = {
        "direction": (
            _wts_direction_parameters(),
            {"doc": "Define the direction of the primary particles.", "override": True},
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()
        self._dir_validator = WTSDirectionValidator()
        self._dir_validator.set_simulation(self.simulation)

    def __initcpp__(self):
        g4.GateWindowTurboSource.__init__(self)

    def initialize(self, run_timing_intervals):
        self._pos_validator.validate(self, "position")
        self._ene_validator.validate(self, "energy")
        self._dir_validator.validate(self, "direction")

        if self.particle == "back_to_back":
            fatal(
                "The 'back_to_back' particle type is not compatible with WindowTurboSource."
            )
        if self.n > 0:
            fatal("The 'n' parameter is not compatible with WindowTurboSource.")

        if self.particle != "gamma":
            warning(
                f"Particle type '{self.particle}' is not 'gamma'. WindowTurboSource is designed for gamma primary purpose only. Proceed ONLY if you know what you are doing."
            )

        self.update_tac_activity()

        ene = self.energy
        if ene.type == "histogram":
            if len(ene.histogram_weight) != len(ene.histogram_energy):
                fatal(
                    f'For the source {self.name}, the parameters "energy", '
                    f'"histogram_energy" and "histogram_weight" must have the same length'
                )
        if self.half_life > 0:
            # if the user set the half life and not the user_particle_life_time
            # we force the latter to zero
            if self.user_particle_life_time < 0:
                self.user_particle_life_time = 0

        # initialize
        SourceBase.initialize(self, run_timing_intervals)

    def can_predict_number_of_events(self):
        # Actually, can, but initialization is needed. However act ratio is dependent on mother volume movement, therefore cannot be predicted before the simulation starts.
        return False

    def validate_color(self, color):
        valid_color_str = [
            "white",
            "grey",
            "gray",
            "black",
            "brown",
            "red",
            "green",
            "blue",
            "cyan",
            "magenta",
            "yellow",
        ]
        if isinstance(color, str) and not color in valid_color_str:
            fatal(
                f"Invalid color name '{color}' for visualizing the window. Valid color name options are: {valid_color_str}."
            )
        if isinstance(color, list):
            if len(color) > 4 or len(color) < 3:
                fatal(
                    f"Color list must have 3 (RGB) or 4 (RGBA) elements. Got {len(color)}."
                )
            if len(color) == 3:
                color.append(1.0)  # Add alpha value of 1.0 if only RGB is provided
                logger.info(
                    "Alpha value of 1.0 is added to the color list since only RGB values are provided."
                )
            for i, c in enumerate(color):
                if not isinstance(c, (int, float, np.number)):
                    fatal(
                        f"All elements of color list must be numbers. Element {i} is not."
                    )
                if c < 0 or c > 1:
                    fatal(
                        f"All elements of color list must be in the range [0, 1]. Element {i} is {c}."
                    )

    def visualize_window(
        self, color, width: float = 2.0, timing_interval_index: int = 0
    ):
        if (
            timing_interval_index >= len(self.simulation.run_timing_intervals)
            or timing_interval_index < 0
        ):
            fatal(
                f"Invalid timing interval index {timing_interval_index}. Must be between 0 and {len(self.simulation.run_timing_intervals) - 1}."
            )
        self.validate_color(color)
        if isinstance(color, str):
            color = color.lower()
            self.VisualizeWindowWithColourName(color, width, timing_interval_index)
        else:
            self.VisualizeWindowWithRGBA(color, width, timing_interval_index)


process_cls(WindowTurboSource)
