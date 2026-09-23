# Skill: `engineering/geant4-geometry-expert`

**Role:** work at the *raw Geant4 geometry* layer — G4 solids, logical/physical volumes,
placements, materials, navigation, overlaps, and the C++ side of geometry in `core/`. Use this
when the GATE-level API in [`gate-geometry-expert.md`](gate-geometry-expert.md) is not enough, or
when you must understand what GATE is really building.

Read [`gate-geometry-expert.md`](gate-geometry-expert.md) first if you only need the user-facing
volume API. This skill is the layer *below* it: the G4 concepts, the C++ bindings, and the
engineer-level reasoning about geometry soundness.

---

## 1. When you are in this skill and not the GATE one

| Symptom / need | Skill |
| --- | --- |
| Add or move a volume with `sim.volume_manager` | [`gate-geometry-expert.md`](gate-geometry-expert.md) |
| Add a new solid/shape type, or a new geometry binding | **this skill** + [`../architecture/SKILL.md`](../architecture/SKILL.md) |
| A G4 overlap / navigation error with a G4 class name in the message | **this skill** |
| Explain *why* GATE's repeated-volume or region model behaves as it does | **this skill** |
| Change material handling in `core/` | **this skill** |
| A physics effect you cannot explain from the geometry you wrote | both, in this order |

## 2. Establish the environment before discussing G4 behaviour

Raw-Geant4 reasoning is only valid on the pinned build. Confirm **both**:

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
python -c "from opengate_core import GateInfo; print(GateInfo.get_G4Version())"
opengate_tests -t geometry/test001_g4geometry_geometrymapping.py   # header: 'Geant4 version is OK'
```

GATE 10 pins Geant4 `v11.4.2`. Navigation, overlap detection and solid-vs-solid behaviour differ
between patch levels; do not reason about a G4 class's behaviour on a version you have not
verified you are linked against (`../environment-setup/SKILL.md` §3.3).

## 3. The G4 geometry object model (and where GATE maps onto it)

Geant4 geometry is a strict hierarchy. GATE's `VolumeBase` produces exactly these G4 objects:

| Geant4 concept | GATE object | Where |
| --- | --- | --- |
| `G4VSolid` (a shape, no placement) | `SolidBase` subclasses | `opengate/geometry/solids.py` |
| `G4LogicalVolume` (shape + material + daughters) | the logical volume of a `VolumeBase` | `opengate/geometry/volumes.py` |
| `G4VPhysicalVolume` (a placement of a logical volume in a mother) | the physical volume of a `VolumeBase` (via `g4_physical_volume`) | `opengate/geometry/volumes.py` |
| `G4Region` (set of logical volumes with shared production cuts) | a GATE region | `VolumeManager` |
| `G4Field` / `G4FieldManager` | a field attached by name (`field` user parameter) | `opengate/geometry/fields.py` |
| `G4VUserDetectorConstruction` | built by GATE's engine, not by the user | `opengate/engines.py` + `core/` |

Key consequences you must internalise:

- **A solid is shared; a logical volume owns a material and its daughters; a physical volume is a
  placement.** Two repeated placements of the same detector share the logical volume but have
  distinct physical volumes and distinct unique IDs.
- **The world volume is special**: the top `G4PVPlacement`, the one with no mother, whose logical
  volume must contain everything. GATE creates it in `gate.Simulation()`.
- **Naming is not identity.** In G4, names are labels; identity is by pointer/ID. Two logical
  volumes with the same name in different subtrees are different objects — score by unique ID
  (`GateUniqueVolumeID`), never by name.

## 4. The C++ side in this repo

Geometry-relevant C++ lives under `core/opengate_core/opengate_lib/`:

| File(s) | Purpose |
| --- | --- |
| `GateGeometryUtils`, `GateHelpersGeometry` | GATE-level geometry helpers exposed to Python |
| `GateUniqueVolumeID`, `GateUniqueVolumeIDManager` | stable identity for a placement |
| `GateVolumeVoxelizer` | voxelise a volume (used by imaging/dose workflows) |
| `pyGate*.cpp` | the pybind11 wrapper registering each class in `core/opengate_core.cpp` |

Rules:

- **Never invent a G4 class name.** Grep `core/` and the Geant4 headers you are actually linked
  against before writing one.
- Adding a new geometry binding means: implement the class, add a `py…` wrapper, **register it in
  `core/opengate_core/opengate_core.cpp`**, then rebuild. An editable install does **not** pick up
  C++ changes — the `.so` is stale until you rebuild, and the failure is a misleading
  `AttributeError: module 'opengate_core' has no attribute 'Gate…'`
  (`../environment-setup/SKILL.md` §4.6).
- Rebuild with the **incremental** path (`cmake` + `make` in `core/build/cmake.*`), parallelism via
  `os.cpu_count()` / `OPEN_GATE_BUILD_JOBS` (B-007).

## 5. Placement, rotation and repetition in G4 terms

- A placement is a rotation **then** translation in the mother's frame; GATE's `rotation` +
  `translation` user parameters map one-to-one onto the G4 transform. Rotation is a 3×3 matrix;
  translation is a 3-vector.
- **Repetition** in GATE is a *list* of transforms on a single `VolumeBase`, expanded to N
  physical volumes — it is not `G4Replica`/`G4Parameterised`. This matters when you need
  parameterised behaviour: for those cases use GATE's own parametrisation/`TesselatedSolid`
  paths, or the C++ building blocks, rather than expecting replica semantics.
- **The transform is relative to the mother**, so moving a mother moves its whole subtree. When a
  daughter lands in the wrong place, walk the tree from the world down and check each transform,
  not just the one you edited.

## 6. Materials in G4 terms

- GATE uses the **Geant4 NIST material database** for `G4_*` names; a custom material must be
  defined (elements, isotope composition, density) before any volume references it, or
  initialisation fails.
- Density is in G4 units internally; a wrong-by-10× density is a silent, systematic scaling of
  every interaction length. It is the classic "everything is off by a constant" geometry cause.
- **HU / voxel materials** are a GATE layer over this: an image gives material indices, a table
  maps HU→material and HU→density with an interpolation. The table and interpolation are
  modelling choices with dosimetry impact — state them.
- Materials are shared objects: changing one changes every volume using it. Prefer defining a
  distinct material over mutating a shared one.

## 7. Overlaps, navigation and "daughter outside mother"

These are the G4-level failures that bite hardest because they often do **not** stop the run.

- **Overlap** — two physical volumes occupy the same space. GATE/Geant4 can detect this; read the
  report. Rays through an overlap see duplicated or skipped material: dose, fluence and
  coincidence counts shift plausibly but wrongly.
- **Daughter outside mother** — a daughter's extent exceeds the mother's; tracks may be lost at
  the boundary and scoring volumes silently miss.
- **Tolerance** — G4 compares extents with a tolerance. A shape that only *just* fits may be
  flagged or may not, depending on tolerance and patch level; do not design geometry that relies
  on exact coincidence of surfaces.
- **Assert, do not eyeball.** Convert the checks you care about into explicit comparisons: walk
  the tree, compare each daughter's bounding box against its mother's
  (`SolidBase.bounding_limits` / `bounding_box_size`), and assert containment with the tolerance
  you intend.

## 8. Debugging raw-geometry problems

1. **Classify first** — a G4 error message with a G4 class name is usually a real geometry
   problem; a missing `Gate…` attribute is a *stale build*
   ([`simulation-debugger.md`](simulation-debugger.md) §1).
2. **Reduce to the minimal tree** — world + your two volumes. If the overlap disappears, bisect by
   adding volumes back.
3. **Print the transforms and bounding boxes** for the subtree in question; compare the world-space
   extents by hand.
4. **Check units at the boundary** — a unit error is a *scale* error in the transform or the
   solid's dimensions, and is invisible in a successful run.
5. **Check the region/cut assignment** at the same time: a geometry that is fine but assigned to
   the wrong region gives wrong physics with no error.
6. **Vary one thing at a time** and predict the expected change before re-running, so "it changed"
   becomes "it changed by the amount I predicted".

## 9. Geometry-sensitive checks worth making explicit

- **Containment**: every daughter inside its mother, with the tolerance you intend.
- **Non-overlap**: no two physical volumes share space (or, if they must, the reason is written).
- **Alignment**: voxelised/boundary-critical geometry asserted on a few known voxels or edges.
- **Consistency of repeated placements**: same length for `translation` and `rotation` lists.
- **Material**: the intended density/composition on at least one known volume.
- **Solid angle**: for a detector meant to see a source, the predicted fraction vs. the modelled
  one — a strong end-to-end geometry check.

## 10. Definition of done

- [ ] Environment proven correct and linked Geant4 version confirmed (pinned `v11.4.2`).
- [ ] The G4 mapping stated: which solid, logical and physical volumes, and in which mother.
- [ ] No invented G4 class names — every one grepped in `core/` or the linked headers.
- [ ] If C++ changed: class registered in `opengate_core.cpp`, `.so` **rebuilt**, warning gone.
- [ ] Overlap / containment / tolerance checked explicitly, not assumed.
- [ ] Units and density sanity-checked on at least one known quantity.
- [ ] Repeated placements have consistent `translation`/`rotation` list lengths.
- [ ] Any geometry change with a physics consequence is justified against
      [`gate-geometry-expert.md`](gate-geometry-expert.md) and
      [`geant4-physics-expert.md`](geant4-physics-expert.md).
