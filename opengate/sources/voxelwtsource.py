import itk

import opengate_core as g4

from .windowturbosource import WindowTurboSource
from .voxelsources import VoxelSource
from ..utility import ensure_filename_is_str
from ..base import process_cls


class VoxelWTSource(WindowTurboSource, g4.GateVoxelWTSource):
    # basically the same as VoxelSource, just avoiding diamond inheritance

    # hints for IDE
    image: str

    user_info_defaults = VoxelSource.user_info_defaults

    def __init__(self, *args, **kwargs):
        VoxelSource.__init__(self, *args, **kwargs)

    def __initcpp__(self):
        g4.GateVoxelWTSource.__init__(self)

    def set_transform_from_user_info(self):
        VoxelSource.set_transform_from_user_info(self)

    def cumulative_distribution_functions(self):
        VoxelSource.cumulative_distribution_functions(self)

    def initialize(self, run_timing_intervals):

        self.itk_image = itk.imread(ensure_filename_is_str(self.image))

        # compute position
        self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()

        self.super().initialize(run_timing_intervals)


process_cls(VoxelWTSource)
