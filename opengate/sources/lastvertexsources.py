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
        # FIXME: deriving source.n from the number of run timing intervals is
        # configuration resolution, not runtime initialization. This should
        # probably move into resolve_and_validate_config().
        self.user_info.n = np.zeros(len(run_timing_intervals)) + 1
        self.initialize_start_end_time(run_timing_intervals)
        self.check_ui_activity(self.user_info)
        g4_source.InitializeUserInfo(self.user_info)


process_cls(LastVertexSource)
