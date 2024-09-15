import tables
import numpy as np

from opengate.postprocessors.image import (
    create_projection_from_positions,
    write_image_with_pytables,
)

# ******
# This test is work in progress to try the experimental postprocessor subpackage.
# Disregard for the moment.
# ******


n_rows = 1000
x = np.random.randn(n_rows) * 20
y = np.random.randn(n_rows) * 20
z = np.ones_like(x)
positions = np.vstack((x, y, z)).T
size = [100, 100, 1]
spacing = [1, 1, 1]

output_file_handle = tables.open_file("test.h5", "w")
hdf5_group = output_file_handle.create_group("/", "projector")

projection = create_projection_from_positions(positions, size, spacing)
path_to_image = ".test072_projection.h5"
with tables.open_file(path_to_image, "w") as f:
    group_path_in_image_file = write_image_with_pytables(projection, file_handle=f)
    output_file_handle.create_external_link(
        hdf5_group, "proj_test", f"{str(path_to_image)}:{group_path_in_image_file}"
    )
