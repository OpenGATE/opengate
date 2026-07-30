import copy
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
    The source used to replay position, energy, direction and weight of last vertex particles actor
    """

    def __init__(self, *args, **kwargs):
        SourceBase.__init__(self, *args, **kwargs)

    def create_g4_source(self):
        return g4.GateLastVertexSource()

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        # FIXME: deriving source.number_of_primaries from the number of run timing intervals is
        # configuration resolution, not runtime initialization. This should
        # probably move into resolve_and_validate_config().
        self.initialize_start_end_time(run_timing_intervals)
        runtime_user_info = copy.deepcopy(self.user_info)
        runtime_user_info.number_of_primaries = (
            np.zeros(len(run_timing_intervals), dtype=int) + 1
        )
        self.check_ui_activity(runtime_user_info)
        if self.simulation.multithreaded:
            runtime_user_info.number_of_primaries = self._scale_counts_for_thread(
                runtime_user_info.number_of_primaries,
                self._get_runtime_thread_index(g4_source),
                int(self.simulation.number_of_threads),
            )
        g4_source.InitializeUserInfo(runtime_user_info)


process_cls(LastVertexSource)
