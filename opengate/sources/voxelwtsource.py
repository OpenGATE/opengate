import itk

import opengate_core as g4

from .windowturbosource import WindowTurboSource
from .voxelsources import VoxelSource
from ..utility import ensure_filename_is_str
from ..base import process_cls
from ..actors.dynamicactors import SourceActivityImageChanger


class VoxelWTSource(WindowTurboSource):
    # basically the same as VoxelSource, just avoiding diamond inheritance

    # hints for IDE
    image: str

    user_info_defaults = VoxelSource.user_info_defaults

    def __init__(self, *args, **kwargs):
        WindowTurboSource.__init__(self, *args, **kwargs)
        # the loaded image
        self._current_itk_image = None
        # cached CDFs
        self._cdf_x = None
        self._cdf_y = None
        self._cdf_z = None

    def create_g4_source(self):
        g4_source = g4.GateVoxelWTSource()
        g4_source.SetSharedCache(self._g4_shared_cache)
        return g4_source

    def create_changers(self):
        changers = super().create_changers()
        for dp in self.dynamic_params.values():
            if dp["extra_params"]["auto_changer"] is True:
                if "image" in dp:
                    new_changer = SourceActivityImageChanger(
                        name=f"{self.name}_source_activity_changer_{len(changers)}",
                        activity_images=dp["image"],
                        attached_to=self,
                        simulation=self.simulation,
                    )
                    changers.append(new_changer)
            else:
                self.warning(
                    f"You need to manually create a changer for dynamic parametrisation {dp} "
                    f"of source '{self.name}'."
                )
        return changers

    def set_transform_from_user_info(self, g4_source):
        VoxelSource.set_transform_from_user_info(self, g4_source)

    def cumulative_distribution_functions(self, g4_source):
        VoxelSource.cumulative_distribution_functions(self, g4_source)

    def update_activity_image(self, filename):
        VoxelSource.update_activity_image(self, filename)

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        if self._current_itk_image is None:
            self._current_itk_image = itk.imread(ensure_filename_is_str(self.image))
        self.set_transform_from_user_info(g4_source)
        self.cumulative_distribution_functions(g4_source)
        WindowTurboSource.initialize_g4_source(self, g4_source, run_timing_intervals)


process_cls(VoxelWTSource)
