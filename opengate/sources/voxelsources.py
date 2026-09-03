import itk

import opengate_core as g4
from .generic import GenericSource
from ..image import (
    get_info_from_image,
    update_image_py_to_cpp,
    compute_image_3D_CDF,
)
from ..utility import ensure_filename_is_str, warning
from ..base import process_cls
from ..actors.dynamicactors import SourceActivityImageChanger


class VoxelSource(GenericSource):
    """
    VoxelSource = 3D activity distribution.
    Sampled with cumulative distribution functions.
    """

    # hints for IDE
    image: str

    user_info_defaults = {
        "image": (
            None,
            {
                # FIXME: this file-backed input is still modeled as a plain
                # string-like parameter. Consider migrating to Path-based user
                # info handling consistently across serialized inputs.
                "doc": "Filename of the image of the 3D activity distribution "
                "(will be automatically normalized to sum=1)",
                "is_input_file": True,
                "dynamic": True,
            },
        )
    }

    def __init__(self, *args, **kwargs):
        GenericSource.__init__(self, *args, **kwargs)
        # the loaded image
        self._current_itk_image = None
        # cached CDFs
        self._cdf_x = None
        self._cdf_y = None
        self._cdf_z = None

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
        src_info = get_info_from_image(self._current_itk_image)
        # get the pointer to SPSVoxelPosDistribution
        pg = g4_source.GetSPSVoxelPosDistribution()
        # update cpp image info (no need to allocate)
        update_image_py_to_cpp(self._current_itk_image, pg.cpp_edep_image, False)
        # set spacing
        pg.cpp_edep_image.set_spacing(src_info.spacing)
        # set origin (half size + translation and half-pixel shift)
        c = (
            -src_info.size / 2.0 * src_info.spacing
            + self.position.translation
            + src_info.spacing / 2.0
        )
        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self, g4_source):
        """
        Compute the Cumulative Distribution Function of the image
        Composed of: CDF_Z = 1D, CDF_Y = 2D, CDF_X = 3D
        """
        if self._cdf_x is None or self._cdf_y is None or self._cdf_z is None:
            self._cdf_x, self._cdf_y, self._cdf_z = compute_image_3D_CDF(
                self._current_itk_image
            )

        # set CDF to the position generator
        pg = g4_source.GetSPSVoxelPosDistribution()
        pg.SetCumulativeDistributionFunction(self._cdf_z, self._cdf_y, self._cdf_x)

    def update_activity_image(self, filename):
        # read source image
        self._current_itk_image = itk.imread(ensure_filename_is_str(filename))

        # Reset CDF cache
        self._cdf_x = None
        self._cdf_y = None
        self._cdf_z = None

        # update all thread-local sources
        for g4_source in self.g4_thread_sources:
            # compute position
            self.set_transform_from_user_info(g4_source)
            # create Cumulative Distribution Function
            self.cumulative_distribution_functions(g4_source)

    def create_g4_source(self):
        return g4.GateVoxelSource()

    def initialize_g4_source(self, g4_source, run_timing_intervals):
        if self._current_itk_image is None:
            self._current_itk_image = itk.imread(ensure_filename_is_str(self.image))
        self.set_transform_from_user_info(g4_source)
        self.cumulative_distribution_functions(g4_source)
        # initialise standard options (particle energy, etc.)
        GenericSource.initialize_g4_source(self, g4_source, run_timing_intervals)


class VoxelizedPromptGammaTLESource(VoxelSource):
    """
    VoxelizedPromptGammaTLESource = 3D PG distribution.
    Sampled with cumulative distribution functions.
    """

    def create_g4_source(self):
        return g4.GateVoxelizedPromptGammaTLESource()


process_cls(VoxelSource)
process_cls(VoxelizedPromptGammaTLESource)
