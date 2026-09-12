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

## Synthetic example phantom

- Removed the previously committed MRCP heart/lung `.node`, `.ele`, and
  `.material` files because their redistribution license still requires
  confirmation.
- Removed the associated `colour.dat` file.
- Added an independently created `simple` dataset containing three
  non-overlapping shapes: a sphere approximated by
  20 tetrahedra (region 100), a cube split into six tetrahedra (region 200),
  and one regular tetrahedron (region 300).
- Added a separate `letter` dataset containing a three-dimensional `GATE`
  label derived from Times New Roman Bold outlines. Each letter is made from
  slightly separated, non-overlapping cells subdivided into tetrahedra:
  G (region 400), A (region 500), T (region 600), and E (region 700).
- `simple.node` contains 25 nodes and 27 tetrahedra. `letter.node` contains
  1200 nodes and 900 tetrahedra.
- All seven regions use independent synthetic material definitions and
  distinct visualization colors.
- `mrcp_simple.py` loads only `simple.node`, `simple.ele`, `simple.material`,
  and `simple_colour.dat`.
- The old combined `sample.*` files were removed.
- The synthetic datasets are intended for input, initialization,
  visualization, and basic
  geometry validation without requiring redistribution of an anatomical
  phantom dataset.

## Validation and repository status

- `git diff --check` completed without whitespace errors.
- The OpenGATE core compiled successfully after the C++ node-reader changes.
- Both OpenGATE 10.1.0 and 10.1.1 initialized and ran the synthetic sample
  successfully with visualization disabled during automated validation.
- Both versions completed tetrahedral overlap checking for the separated simple
  shapes without an overlap warning.
- The letter dataset passed node/element index validation; all 150 letter-cell
  bounding boxes are separated and do not intersect.
- The only runtime warning reported that no particle source was configured,
  which is expected for this geometry-only example.
- OpenGATE 10.1.0 was committed and pushed as `c06dd0b9f` on branch
  `mrcp-tet-phantom-10.1.0`.
- OpenGATE 10.1.1 was committed and pushed as `7fc0f799b` on branch
  `mrcp-tet-phantom-10.1.1`.
