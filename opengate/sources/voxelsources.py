import os
from pathlib import Path

import itk

import opengate_core as g4
from .generic import GenericSource
from ..image import (
    get_info_from_image,
    update_image_py_to_cpp,
    compute_image_3D_CDF,
    check_image_direction_is_identity,
)
from ..utility import ensure_filename_is_str, warning
from ..base import process_cls
from ..actors.dynamicactors import SourceActivityImageChanger

# The activity images and the alias tables of the voxel sources, shared by
# the sources that read the same image file (e.g. copies of one source) and
# by the thread-local sources: one copy in memory. Key: the resolved path,
# the modification time and the size of the file. Cleared when the sources
# are closed (end of the simulation).
_shared_voxel_source_data = {"images": {}, "tables": {}}


def _image_key(filename):
    p = Path(ensure_filename_is_str(filename)).resolve()
    try:
        st = os.stat(p)
        return str(p), st.st_mtime_ns, st.st_size
    except OSError:
        return None


def clear_shared_voxel_source_data():
    _shared_voxel_source_data["images"].clear()
    _shared_voxel_source_data["tables"].clear()


class VoxelSource(GenericSource):
    """
    VoxelSource = 3D activity distribution.
    Sampled with an alias table built from the cumulative distribution
    functions (CDFs) of the image. The image and the table are shared by the
    sources (and the thread-local sources) that read the same image file.
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
        # the loaded image (shared with the sources with the same file)
        self._current_itk_image = None
        self._current_image_key = None
        # the alias table of the image (C++, shared), see
        # cumulative_distribution_functions ("g4_" in the name: set to None
        # by close)
        self._g4_alias_table = None
        # indices (in g4_thread_sources) of the thread-local g4 sources which
        # already received the table (see cumulative_distribution_functions)
        self._cdf_applied_g4_sources = set()

    def close(self):
        clear_shared_voxel_source_data()
        super().close()

    def load_activity_image(self, filename):
        """Read the image (or take it from the shared data if another source
        already read the same file)."""
        key = _image_key(filename)
        images = _shared_voxel_source_data["images"]
        if key is not None and key in images:
            img = images[key]
        else:
            img = itk.imread(ensure_filename_is_str(filename))
            check_image_direction_is_identity(
                img, f"the voxel source '{self.name}' ({filename})"
            )
            if key is not None:
                images[key] = img
        self._current_itk_image = img
        self._current_image_key = key

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
        Give the alias table of the image to the position generator of the
        g4 source. The table is built once per image file, from the CDFs
        (CDF_Z = 1D, CDF_Y = 2D, CDF_X = 3D, not kept), and shared by the
        thread-local sources and by the other sources with the same image.
        """
        # Each thread-local source is initialised twice in MT: on the main thread
        # (SourceEngine.create_master_source_manager) and again by its Geant4
        # worker thread. The table is only given the first time (see #1163).
        # (no reference to the g4 sources is kept here: they must be deleted
        # with g4_thread_sources, on the main thread, at the end)
        index = next(
            (i for i, s in enumerate(self.g4_thread_sources) if s is g4_source), None
        )
        if index is not None and index in self._cdf_applied_g4_sources:
            return

        pg = g4_source.GetSPSVoxelPosDistribution()
        tables = _shared_voxel_source_data["tables"]
        key = self._current_image_key
        if self._g4_alias_table is None and key is not None:
            self._g4_alias_table = tables.get(key)
        if self._g4_alias_table is None:
            # build the table from the CDFs (the expensive part, once)
            cdf_x, cdf_y, cdf_z = compute_image_3D_CDF(self._current_itk_image)
            pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)
            del cdf_x, cdf_y, cdf_z
            self._g4_alias_table = pg.GetAliasTable()
            if key is not None:
                tables[key] = self._g4_alias_table
        else:
            pg.SetAliasTable(self._g4_alias_table)
        if index is not None:
            self._cdf_applied_g4_sources.add(index)

    def pre_create_g4_sources(self, num_instances):
        # new thread-local sources: none of them has the CDFs yet
        self._cdf_applied_g4_sources = set()
        super().pre_create_g4_sources(num_instances)

    def update_activity_image(self, filename):
        # read source image
        self.load_activity_image(filename)
        # the image changed: every thread-local source needs the new table
        self._g4_alias_table = None
        self._cdf_applied_g4_sources = set()

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
            self.load_activity_image(self.image)
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
