import os
import copy
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
    number_of_primaries: int
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
        "number_of_primaries": (
            0,
            {
                "doc": "Number of primaries to generate (exclusive with 'activity')",
            },
        ),
        "n": (
            0,
            {
                "deprecated": "The user input parameter 'n' is deprecated. Use 'number_of_primaries' instead.",
            },
        ),
        "activity": (
            0,
            {
                "doc": "Activity of the source in Bq (exclusive with 'number_of_primaries')",
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
        if self.start_time is None:
            self.start_time = run_timing_intervals[0][0]
        if self.end_time is None:
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

    def _get_runtime_thread_index(self, g4_source):
        if not self.simulation.multithreaded:
            return 0

        if self.g4_thread_sources:
            try:
                g4_source_index = self.g4_thread_sources.index(g4_source)
            except ValueError:
                g4_source_index = None
            if g4_source_index is not None and g4_source_index > 0:
                return g4_source_index - 1

        thread_id = g4.G4GetThreadId()
        if thread_id >= 0:
            return thread_id
        return 0

    @staticmethod
    def _scale_counts_for_thread(counts, thread_index, number_of_threads):
        counts = np.asarray(counts, dtype=int)
        counts_per_thread = counts // number_of_threads
        remainders = counts % number_of_threads
        extra = np.asarray(thread_index < remainders, dtype=int)
        return counts_per_thread + extra

    def build_runtime_user_info_for_g4_source(self, g4_source):
        # Build a runtime-facing top-level copy without deep-copying Python-side
        # helper objects stored in user_info, e.g. GAN generators. The runtime
        # adapter only rewrites a small set of top-level source parameters.
        runtime_user_info = self.user_info.copy()

        if self.simulation.multithreaded:
            number_of_threads = int(self.simulation.number_of_threads)
            thread_index = self._get_runtime_thread_index(g4_source)

            if np.any(runtime_user_info.number_of_primaries > 0):
                runtime_user_info.number_of_primaries = self._scale_counts_for_thread(
                    runtime_user_info.number_of_primaries,
                    thread_index,
                    number_of_threads,
                )
            if runtime_user_info.activity > 0:
                runtime_user_info.activity = (
                    runtime_user_info.activity / number_of_threads
                )
            if (
                hasattr(runtime_user_info, "tac_activities")
                and runtime_user_info.tac_activities is not None
            ):
                runtime_user_info.tac_activities = (
                    np.asarray(runtime_user_info.tac_activities, dtype=float)
                    / number_of_threads
                )

        # C++ source initializers expect ordinary Python containers here.
        # Keep the numpy-based normalization internal to Python and hand off
        # plain lists once runtime scaling is complete.
        runtime_user_info.number_of_primaries = np.asarray(
            runtime_user_info.number_of_primaries, dtype=int
        ).tolist()
        if (
            hasattr(runtime_user_info, "tac_activities")
            and runtime_user_info.tac_activities is not None
        ):
            runtime_user_info.tac_activities = np.asarray(
                runtime_user_info.tac_activities, dtype=float
            ).tolist()

        if hasattr(runtime_user_info, "to_dict"):
            return runtime_user_info.to_dict()
        return dict(runtime_user_info)

    def gather_outputs(self, thread_sources):
        pass

    def recover_user_output(self, s):
        pid = os.getpid()
        print(f"(python) recover_user_output {self.name} pid={pid}")
        for k, v in s.user_info.items():
            self.user_info[k] = v

    def can_predict_number_of_events(self):
        return True

    def resolve_and_validate_config(self, run_timing_intervals, context=None):
        self.resolve_and_validate_timing(run_timing_intervals)
        if np.array([self.user_info.number_of_primaries]).shape == (1,):
            self.user_info.number_of_primaries = np.array(
                [self.user_info.number_of_primaries], dtype=int
            )
        else:
            self.user_info.number_of_primaries = np.array(
                self.user_info.number_of_primaries, dtype=int
            )
        if (self.user_info.activity == 0) and (
            len(self.user_info.number_of_primaries) != len(self.run_timing_intervals)
        ):
            fatal(
                "source.number_of_primaries and run_timing_intervals do not have the same length."
            )
        if (
            np.any(self.user_info.number_of_primaries > 0)
            and self.user_info.activity > 0
        ):
            fatal(
                "Cannot use both the two parameters 'number_of_primaries' and 'activity' at the same time. "
            )
        if (
            np.all(self.user_info.number_of_primaries == 0)
            and self.user_info.activity == 0
        ):
            fatal(
                "You must set one of the two parameters 'number_of_primaries' or 'activity'."
            )
        if self.user_info.activity > 0:
            self.user_info.number_of_primaries = np.array(
                np.zeros(len(self.run_timing_intervals), dtype=int)
            )
        if np.any(self.user_info.number_of_primaries > 0):
            self.user_info.activity = 0


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
        runtime_user_info = self.build_runtime_user_info_for_g4_source(g4_source)
        g4_source.InitializeUserInfo(runtime_user_info)

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
