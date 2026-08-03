# Tetrahedral Mesh Change Log

## Package cleanup

- Removed `opengate/contrib/mrcp/__init__.py`. It referenced the deleted
  `mrcp.py` module and caused `import opengate` to fail.
- Removed the previous root-level Markdown files whose names started with
  `MRCP_`; they are not intended for the official GitHub pull request.

## TetGen node parsing

- `TetrahedralMeshEnvelopeSolid._read_node_bounds()` now treats the first
  non-comment line as the TetGen header instead of a coordinate record.
- The Python reader verifies that the number of parsed nodes matches the count
  declared in the header.
- The C++ reader collects all indexed coordinates before deciding whether the
  file uses the complete `0..N-1` or `1..N` index range.
- The C++ reader rejects count mismatches, duplicate node IDs, out-of-range
  IDs, and incomplete or mixed index ranges.

## Color data cleanup

- Normalized `opengate/contrib/mrcp/colour.dat` to LF line endings.
- Removed trailing spaces from every color entry.

## Private tetrahedral-volume helpers

- Removed `opengate/contrib/mrcp/mrcp_utils.py`.
- Moved the three required operations into `TetrahedralMeshVolume` as private
  methods: `_parse_mrcp_material_file`,
  `_ensure_custom_material_from_zfrac`, and `_parse_colour_dat`.
- This follows the existing `ImageVolume` pattern of keeping volume-specific
  label/material mapping operations close to the volume implementation.
- Broader material architecture, including possible integration with
  OpenGATE's `MaterialDatabase`, remains a separate design decision.
