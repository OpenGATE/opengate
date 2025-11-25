import numpy as np

from ..actors.base import _setter_hook_attached_to
from ..base import GateObject, process_cls
from ..utility import g4_units
from ..definitions import __world_name__
from ..exception import fatal, warning


class SourceBase(GateObject):
    """
    Base class for all source types.
    """

    # hints for IDE
    attached_to: str
    mother: str
    start_time: float
    end_time: float
    n: int
    activity: float
    half_life: float

    user_info_defaults = {
        "attached_to": (
            __world_name__,
            {
                "doc": "Name of the volume to which the source is attached.",
                "setter_hook": _setter_hook_attached_to,
            },
        ),
        "mother": (
            None,
            {
                "deprecated": "The user input parameter 'mother' is deprecated. Use 'attached_to' instead. ",
            },
        ),
        "start_time": (
            None,
            {
                "doc": "Starting time of the source",
            },
        ),
        "end_time": (
            None,
            {
                "doc": "End time of the source",
            },
        ),
        "n": (
            0,
            {
                "doc": "Number of particle to generate (exclusive with 'activity')",
            },
        ),
        "activity": (
            0,
            {
                "doc": "Activity of the source in Bq (exclusive with 'n')",
            },
        ),
        "half_life": (
            -1,
            {
                "doc": "Half-life decay (-1 if no decay). Only when used with 'activity'",
            },
        ),
    }

    def __init__(self, *args, **kwargs):
        GateObject.__init__(self, *args, **kwargs)
        # all times intervals
        self.run_timing_intervals = None

    def __initcpp__(self):
        """Nothing to do in the base class."""

    def __setstate__(self, state):
        super().__setstate__(state)
        self.__initcpp__()

    def dump(self):
        sec = g4_units.s
        start = "no start time"
        end = "no end time"
        if self.user_info.start_time is not None:
            start = f"{self.user_info.start_time / sec} sec"
        if self.user_info.end_time is not None:
            end = f"{self.user_info.end_time / sec} sec"
        s = (
            f"Source name        : {self.user_info.physics_list_name}\n"
            f"Source type        : {self.user_info.type}\n"
            f"Start time         : {start}\n"
            f"End time           : {end}"
        )
        return s

    def initialize_source_before_g4_engine(self, source):
        pass

    def initialize_start_end_time(self, run_timing_intervals):
        self.run_timing_intervals = run_timing_intervals
        # by default, consider the source time start and end like the whole simulation
        # Start: start time of the first run
        # End: end time of the last run
        if not self.start_time:
            self.start_time = run_timing_intervals[0][0]
        if not self.end_time:
            self.end_time = run_timing_intervals[-1][1]

    def initialize(self, run_timing_intervals):
        self.initialize_start_end_time(run_timing_intervals)
        # this will initialise and set user_info to the cpp side
        self.check_ui_activity(self.user_info)
        self.InitializeUserInfo(self.user_info)

    def add_to_source_manager(self, source_manager):
        source_manager.AddSource(self)

    def prepare_output(self):
        pass

    def can_predict_number_of_events(self):
        return True

    def check_ui_activity(self, ui):
        # FIXME: This should rather be a function than a method
        # FIXME: self actually holds the parameters n and activity, but the ones from ui are used here.
        # Old fix_me do not knwo if it's still valid
        if np.array([ui.n]).shape == (1,):
            ui.n = np.array([ui.n], dtype=int)
        else:
            ui.n = np.array(ui.n, dtype=int)
        if (ui.activity == 0) and (len(ui.n) != len(self.run_timing_intervals)):
            fatal(f"source.n and run_timing_intervals do not have the same length.")
        if np.any(ui.n > 0) and ui.activity > 0:
            fatal(
                f"Cannot use both the two parameters 'n' and 'activity' at the same time. "
            )
        if np.all(ui.n == 0) and ui.activity == 0:
            fatal(f"You must set one of the two parameters 'n' or 'activity'.")
        if ui.activity > 0:
            ui.n = np.array(np.zeros(len(self.run_timing_intervals), dtype=int))
        if np.any(ui.n > 0):
            ui.activity = 0


process_cls(SourceBase)
