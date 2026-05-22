import itk

import opengate_core as g4

from .windowturbosource import WindowTurboSource
from .voxelsources import VoxelSource
from ..utility import ensure_filename_is_str
from ..base import process_cls
from ..actors.dynamicactors import SourceActivityImageChanger


class VoxelWTSource(WindowTurboSource, g4.GateVoxelWTSource):
    # basically the same as VoxelSource, just avoiding diamond inheritance

    # hints for IDE
    image: str

    user_info_defaults = VoxelSource.user_info_defaults

    def __init__(self, *args, **kwargs):
        self.__initcpp__()
        super().__init__(self, *args, **kwargs)
        # the loaded image
        self._current_itk_image = None

    def __initcpp__(self):
        g4.GateVoxelWTSource.__init__(self)

    def create_changers(self):
        return VoxelSource.create_changers(self)

    def create_changers_bak(self):
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

    def set_transform_from_user_info(self):
        VoxelSource.set_transform_from_user_info(self)

    def cumulative_distribution_functions(self):
        VoxelSource.cumulative_distribution_functions(self)

    def update_activity_image(self, filename):

        self._current_itk_image = itk.imread(ensure_filename_is_str(filename))

        # compute position
        self.set_transform_from_user_info()

        # create Cumulative Distribution Function
        self.cumulative_distribution_functions()

    def initialize(self, run_timing_intervals):
        self.update_activity_image(self.image)

        super().initialize(run_timing_intervals)


process_cls(VoxelWTSource)
