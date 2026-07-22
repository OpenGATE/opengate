import os
import numpy as np
import opengate_core as g4

from ..actors.base import _setter_hook_attached_to
from ..base import GateObject, DynamicGateObject, process_cls
from ..utility import g4_units
from ..definitions import __world_name__
from ..exception import fatal, warning


class SourceBase(DynamicGateObject):
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
        self.g4_thread_sources = []
        self.g4_thread_sources_index = 0

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

    def resolve_and_validate_timing(self, run_timing_intervals):
        # Resolve implicit source time bounds against the master simulation
        # timeline before any child jobs or runtime engines reinterpret them.
        self.initialize_start_end_time(run_timing_intervals)

    def initialize(self, run_timing_intervals):
        self.initialize_start_end_time(run_timing_intervals)
        # The source configuration is expected to have been resolved already by
        # resolve_and_validate_config(); initialize() should only forward the
        # resolved user_info to the runtime layer.
        self.InitializeUserInfo(self.user_info)

    def add_to_source_manager(self, source_manager):
        if hasattr(self, "g4_source") and self.g4_source is not None:
            source_manager.AddSource(self.g4_source)
        else:
            source_manager.AddSource(self)

    def close(self):
        # remove the g4 objects
        for v in list(self.__dict__.keys()):
            if "g4_" in v:
                self.__dict__[v] = None
        # close the base GateObject
        GateObject.close(self)

    def prepare_output(self):
        pass

    def pre_create_g4_sources(self, num_instances):
        self.g4_thread_sources = []
        self.g4_thread_sources_index = 0
        for _ in range(num_instances):
            g4_src = self.create_g4_source()
            if g4_src is not None:
                self.g4_thread_sources.append(g4_src)

    def get_next_g4_source(self):
        if self.g4_thread_sources:
            tid = g4.G4GetThreadId()
            idx = tid + 1 if tid >= 0 else 0
            if idx < len(self.g4_thread_sources):
                return self.g4_thread_sources[idx]
        return None

    def create_g4_source(self):
        return None

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        pass

    def gather_outputs(self, thread_sources):
        pass

    def recover_user_output(self, s):
        pid = os.getpid()
        print(f"(python) recover_user_output {self.name} pid={pid}")
        for k, v in s.user_info.items():
            self.user_info[k] = v

    def can_predict_number_of_events(self):
        return True

    def resolve_and_validate_config(self, run_timing_intervals):
        self.resolve_and_validate_timing(run_timing_intervals)
        self.check_ui_activity(self.user_info)

    def check_ui_activity(self, ui):
        # FIXME: This should rather be a function than a method
        # FIXME: self actually holds the parameters n and activity, but the ones from ui are used here.
        # FIXME: this method validates and also rewrites user_info according to
        # run_timing_intervals. That behavior is part of configuration
        # resolution and should probably be moved into
        # resolve_and_validate_config().
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


class DebugSource(SourceBase):

    user_info_defaults = {
        "debug_flag": (False, {"doc": "Fake parameter."}),
        "debug_value": (0.0, {"doc": "Fake parameter."}),
    }

    def __init__(self, *args, **kwargs):
        pid = os.getpid()
        print(f"(python) DebugSource::__init__ pid={pid}")
        SourceBase.__init__(self, *args, **kwargs)

    def create_g4_source(self):
        pid = os.getpid()
        print(f"(python) DebugSource::create_g4_source pid={pid}")
        return g4.GateDebugSource()

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        pid = os.getpid()
        print(f"(python) DebugSource::initialize_g4_source pid={pid}")
        self.initialize_start_end_time(run_timing_intervals)
        self.check_ui_activity(self.user_info)
        g4_source.InitializeUserInfo(self.user_info)

    def initialize_start_end_time(self, run_timing_intervals):
        pid = os.getpid()
        print(f"(python) DebugSource::initialize_start_end_time {self.name} pid={pid}")
        SourceBase.initialize_start_end_time(self, run_timing_intervals)

    def gather_outputs(self, thread_sources):
        values = [
            g4_src.GetDebugValue() for g4_src in thread_sources if g4_src is not None
        ]
        print(f"(python) DebugSource::gather_outputs values = {values}")
        if values:
            self.debug_value = np.sum(np.array(values))
            print(
                f"(python) DebugSource::gather_outputs selected max value = {self.debug_value}"
            )


process_cls(SourceBase)
process_cls(DebugSource)
