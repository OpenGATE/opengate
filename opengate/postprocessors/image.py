from pathlib import Path

import itk
import numpy as np

import tables

from ..exception import fatal
from .unitbase import ProcessingUnitBase
from .utility import (
    get_table_column_names,
    get_table_column,
    get_node_path,
    filter_nodes,
    get_node_name,
)


class ProjectionListMode(ProcessingUnitBase):
    user_info_defaults = {
        "spacing": (
            [1, 1],
            {
                "doc": "FIXME",
            },
        ),
        "size": (
            [100, 100],
            {
                "doc": "FIXME",
            },
        ),
    }

    def get_input_data(self):
        def has_position_column(table):
            return "position" in get_table_column_names(table)

        input_tables = filter_nodes(
            self.input_units[0].output_data_handles.values(),
            node_type=tables.Table,
            condition_functions=(has_position_column,),
        )
        return input_tables

    def do_your_job(self):
        input_tables = self.get_input_data()
        for i, t in enumerate(input_tables):
            positions = get_table_column(t, "position")
            projection = create_projection_from_positions(
                positions.read(), self.size, self.spacing
            )  # read() returns an array
            output_name = f"projection_{get_node_name(t)}"
            # create a link to the root group in an external image file
            output_group_link = self.get_or_create_output_group(
                "/", link_name=output_name, external_file=True
            )
            # ... and store it in this unit's registry so other units can access it
            output_group = self.register_output_data_handle(output_group_link)
            # write the image into that group
            write_image_with_pytables(projection, group=output_group)


def create_projection_from_positions(positions, size, spacing, origin=None):
    if origin is None:
        origin = [0, 0, 0]

    bins_x = (
        np.linspace(
            -0.5 * size[0] * spacing[0], 0.5 * size[0] * spacing[0], size[0] + 1
        )
        + origin[0]
    )
    bins_y = (
        np.linspace(
            -0.5 * size[1] * spacing[1], 0.5 * size[1] * spacing[1], size[1] + 1
        )
        + origin[1]
    )
    pos_x_binned = np.digitize(positions[:, 0], bins_x)
    pos_y_binned = np.digitize(positions[:, 1], bins_y)
    counts_1d = np.bincount(
        pos_x_binned + (bins_x.size + 1) * pos_y_binned,
        minlength=(bins_x.size + 1) * (bins_y.size + 1),
    )

    # create image in ITK order: z, y, x
    counts_2d = counts_1d.reshape(bins_y.size + 1, bins_x.size + 1)
    binned_image = counts_2d[np.newaxis, 1:-1, 1:-1]

    binned_image_itk = itk.image_view_from_array(binned_image.astype(np.int32))
    binned_image_itk.SetSpacing(spacing)
    binned_image_itk.SetOrigin(origin)

    return binned_image_itk


def write_image_with_pytables(image, group=None, path=None, file_handle=None):
    size = np.asarray(image.GetLargestPossibleRegion().GetSize())
    origin = np.asarray(image.GetOrigin())
    spacing = np.asarray(image.GetSpacing())
    direction = np.asarray(image.GetDirection())
    arr_view = itk.GetArrayViewFromImage(image)
    atom = tables.Atom.from_dtype(arr_view.dtype)
    filters = tables.Filters(complevel=5, complib="zlib")

    # write image via pytables in hdf5 format
    if group is not None:
        _file_handle = group._v_file
        g = group
    else:
        if file_handle is not None:
            _file_handle = file_handle
        else:
            if path is None:
                raise ValueError(
                    f"Path required if no file handle and no group is passed. "
                )
            _file_handle = tables.open_file(path, "w")
        g = _file_handle.root
    try:
        g_itkimage = _file_handle.create_group(g, "ITKImage")
        g_0 = _file_handle.create_group(g_itkimage, "0")

        a_directions = _file_handle.create_array(g_0, "Directions", direction)
        a_spacing = _file_handle.create_array(g_0, "Spacing", spacing)
        a_dimension = _file_handle.create_array(g_0, "Dimension", size)
        a_origin = _file_handle.create_array(g_0, "Origin", origin)

        ca_voxeldata = _file_handle.create_carray(
            g_0, "VoxelData", atom=atom, filters=filters, shape=size[::-1]
        )
        ca_voxeldata[:, :, :] = arr_view

        voxel_type_utf8 = type(image).__name__.encode("utf-8")
        _file_handle.create_array(
            g_0,
            "VoxelType",
            voxel_type_utf8,
            atom=tables.StringAtom(itemsize=len(voxel_type_utf8)),
        )

        _file_handle.create_group(g_0, "MetaData")

        if file_handle is not None:
            return get_node_path(g_0)
    except:
        fatal("Something went wrong while writing an image.")
    finally:
        # close the file if it was created locally
        if file_handle is None:
            _file_handle.close()
