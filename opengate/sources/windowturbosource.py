import opengate_core as g4
from .generic import GenericSource, VisualizationValidator
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


def _wts_visualization_parameters():
    return Box(
        {
            "window_color": [],
            "window_width": [],
            "window_run_id": [],
            "count": 2000,
            "color": "yellow",
            "size": 2,
        }
    )


class WTSDirectionValidator(UserInfoValidatorBase):
    """Validates the 'direction' Box."""

    __schema__ = set(_wts_direction_parameters().keys())

    def set_simulation(self, simulation):
        self.simulation = simulation
        self.act_ratio_inited = True
        self.max_solid_angle_inited = True

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
            logger.debug(
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
        self.num_intervals = len(self.simulation.run_timing_intervals)
        b = getattr(parent_obj, attr_name)

        if isinstance(b.act_ratio, list) and len(b.act_ratio) == 0:
            b.act_ratio = [-1] * self.num_intervals  # default value indicating not set
            self.act_ratio_inited = False
        if isinstance(b.max_solid_angle, list) and len(b.max_solid_angle) == 0:
            b.max_solid_angle = [
                -1
            ] * self.num_intervals  # default value indicating not set
            self.max_solid_angle_inited = False

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
            if (
                max_solid_angle <= 0 or max_solid_angle > 2 * np.pi
            ) and self.max_solid_angle_inited:
                fatal(
                    f"'max_solid_angle' must be in the range (0, 2*pi] for timing interval {int_idx} in '{self.context_name}'."
                )
            act_ratio = self.get_attr_interval(b, "act_ratio", int_idx)
            if (act_ratio < 0 or act_ratio > 1) and self.act_ratio_inited:
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
            logger.debug(
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


class WTSVisualizationValidator(VisualizationValidator):
    """Validates the visualization parameters for WindowTurboSource."""

    __schema__ = set(_wts_visualization_parameters().keys())

    def set_simulation(self, simulation):
        self.simulation = simulation

    def validate_width(self, width, context):
        if not isinstance(width, (int, float)):
            fatal(f"'window_width' must be a number in '{context}'.")
        if width <= 0 or width > 10:
            fatal(f"'window_width' must be in the range (0, 10] in '{context}'.")

    def validate_run_id(self, run_id, context):
        if not isinstance(run_id, int):
            fatal(f"'window_run_id' must be an integer in '{context}'.")

        if run_id < 0 or run_id >= len(self.simulation.run_timing_intervals):
            fatal(
                f"'window_run_id' must be between 0 and {len(self.simulation.run_timing_intervals) - 1} in '{context}'."
            )

    def validate_list_length(self, lst, context):
        if len(lst) == 1:
            lst = lst * self.max_list_length
        elif len(lst) != self.max_list_length:
            fatal(f"Length of list must be 1 or {self.max_list_length} in '{context}'.")

    def validate(self, parent_obj, attr_name: str, parent_context: str = None):
        self.context_name = super().validate(parent_obj, attr_name, parent_context)
        b = getattr(parent_obj, attr_name)
        self.max_list_length = (
            1 if not isinstance(b.window_run_id, list) else len(b.window_run_id)
        )

        if isinstance(b.window_run_id, list):
            for run_id in b.window_run_id:
                self.validate_run_id(run_id, f"{self.context_name}.window_run_id")
        else:
            self.validate_run_id(b.window_run_id, f"{self.context_name}.window_run_id")
            b.window_run_id = [b.window_run_id]

        if not isinstance(b.window_color, list):
            self.validate_color(b.window_color, f"{self.context_name}.window_color[0]")
            b.window_color = [b.window_color] * self.max_list_length
        else:
            for i, color in enumerate(b.window_color):
                self.validate_color(color, f"{self.context_name}.window_color[{i}]")
            self.validate_list_length(
                b.window_color, f"{self.context_name}.window_color"
            )

        if not isinstance(b.window_width, list):
            self.validate_width(b.window_width, f"{self.context_name}")
            b.window_width = [b.window_width] * self.max_list_length
        else:
            for i, width in enumerate(b.window_width):
                self.validate_width(width, f"{self.context_name}")
            self.validate_list_length(
                b.window_width, f"{self.context_name}.window_width"
            )


class WindowTurboSource(GenericSource):
    direction: Box

    user_info_defaults = {
        "direction": (
            _wts_direction_parameters(),
            {"doc": "Define the direction of the primary particles.", "override": True},
        ),
        "visualization": (
            _wts_visualization_parameters(),
            {
                "doc": "Define the visualization parameters for the source.",
                "override": True,
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        GenericSource.__init__(self, *args, **kwargs)
        self._g4_shared_cache = g4.GateWindowTurboSharedCache()
        self._dir_validator = WTSDirectionValidator()
        self._dir_validator.set_simulation(self.simulation)
        self._visu_validator = WTSVisualizationValidator()
        self._visu_validator.set_simulation(self.simulation)

    def create_g4_source(self):
        g4_source = g4.GateWindowTurboSource()
        g4_source.SetSharedCache(self._g4_shared_cache)
        return g4_source

    def initialize_g4_source(self, g4_source, run_timing_intervals):

        if self.particle == "back_to_back":
            fatal(
                "The 'back_to_back' particle type is not compatible with WindowTurboSource."
            )
        if isinstance(self.n, list):
            if any(n_i != 0 for n_i in self.n):
                fatal(
                    "The 'n' parameter must be 0 for all timing intervals in WindowTurboSource."
                )
        elif isinstance(self.n, (int, float)):
            if self.n != 0:
                fatal("The 'n' parameter is not compatible with WindowTurboSource.")
        elif isinstance(self.n, np.ndarray):
            if np.any(self.n != 0):
                fatal(
                    "The 'n' parameter must be 0 for all timing intervals in WindowTurboSource."
                )
        else:
            fatal("Invalid type for 'n' parameter in WindowTurboSource.")

        if self.particle != "gamma":
            warning(
                f"Particle type '{self.particle}' is not 'gamma'. WindowTurboSource is designed for gamma primary purpose only. Proceed ONLY if you know what you are doing."
            )

        GenericSource.initialize_g4_source(self, g4_source, run_timing_intervals)

    def can_predict_number_of_events(self):
        # Actually, can, but initialization is needed. However act ratio is dependent on mother volume movement, therefore cannot be predicted before the simulation starts.
        return False

    def _visualize_window(
        self, color, width: float = 2.0, timing_interval_index: int = 0
    ):
        if (
            timing_interval_index >= len(self.simulation.run_timing_intervals)
            or timing_interval_index < 0
        ):
            fatal(
                f"Invalid timing interval index {timing_interval_index}. Must be between 0 and {len(self.simulation.run_timing_intervals) - 1}."
            )
        self._visu_validator.validate_color(color)
        if isinstance(color, str):
            color = color.lower()
        self.visualization.window_color.append(color)
        self.visualization.window_width.append(width)
        self.visualization.window_run_id.append(timing_interval_index)


process_cls(WindowTurboSource)
