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


class LastVertexSource(SourceBase, g4.GateLastVertexSource):
    """
    The source used to replay position, energy, direction and weight of last vertex particles actor
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__initcpp__()

    def __initcpp__(self):
        g4.GateLastVertexSource.__init__(self)

    def initialize(self, run_timing_intervals):
        self.user_info.n = np.zeros(len(run_timing_intervals)) + 1
        SourceBase.initialize(self, run_timing_intervals)


process_cls(LastVertexSource)
