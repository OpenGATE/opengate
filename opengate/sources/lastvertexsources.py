from box import Box
from scipy.spatial.transform import Rotation

import opengate_core as g4
import numpy as np
from .base import (
    SourceBase,
)
from ..base import process_cls
from ..utility import g4_units
from ..exception import fatal, warning


class LastVertexSource(SourceBase):
    """
    Replay source used by ``LastVertexInteractionSplittingActor``.

    This source does not behave like an ordinary user-driven source. Its
    primaries are reconstructed from last-vertex particle states collected by
    the corresponding splitting actor during transport. The actor later
    injects the replay payload on the C++ side, including the list of stored
    vertices and the number of events to replay.

    In other words, ``LastVertexSource`` is represented as a source in the
    current Python/C++ architecture, but it is operationally driven by
    ``LastVertexInteractionSplittingActor`` rather than by the usual source
    sampling parameters alone.

    ``total_replayed_events`` is gathered from the native sources after transport.
    It counts replay primaries actually generated, excluding fallback geantinos,
    and accumulates across runs independently of the replay queue cursor.
    """

    def __init__(self, *args, **kwargs):
        SourceBase.__init__(self, *args, **kwargs)
        self.total_replayed_events = 0

    def create_g4_source(self):
        return g4.GateLastVertexSource()

    def resolve_and_validate_config(self, run_timing_intervals, context=None):
        # LastVertexSource participates in the generic source resolution
        # cascade, so inherited base-source user_info such as
        # number_of_primaries/activity must stay internally consistent.
        # The actual replay payload and replay count are later overridden on
        # the C++ side by LastVertexInteractionSplittingActor, which owns the
        # authoritative runtime state for this source.
        self.user_info.number_of_primaries = np.ones(
            len(run_timing_intervals), dtype=int
        )
        self.user_info.activity = 0
        # Normalize actor-driven placeholders before the generic validation:
        # the inherited scalar default otherwise fails for multi-run plans.
        super().resolve_and_validate_config(run_timing_intervals, context=context)

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        self.initialize_start_end_time(run_timing_intervals)
        runtime_user_info = self.build_runtime_user_info_for_g4_source(g4_source)
        g4_source.InitializeUserInfo(runtime_user_info)

    def gather_outputs(self, thread_sources):
        self.total_replayed_events = sum(
            source.GetTotalReplayedEvents() for source in thread_sources
        )


process_cls(LastVertexSource)
