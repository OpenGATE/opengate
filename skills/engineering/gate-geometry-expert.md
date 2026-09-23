# Skill: `engineering/gate-geometry-expert`

**Role:** build and verify the *geometry* of a GATE 10 simulation — the volume tree, the solids
that bound it, the materials it is made of, its placement/repetition, and the fields attached to
it — so that the modelled detector is both physically correct and numerically sound.

This skill is the GATE-facing geometry role. It complements
[`geant4-physics-expert.md`](geant4-physics-expert.md) (what happens *inside* the volumes) and
[`python-gate-developer.md`](python-gate-developer.md) (how the classes are structured). Use it
whenever you create or change anything under `sim.volume_manager` / `opengate/geometry/`.

---

## 1. Establish the environment first

Same rule as every physics/geometry role: a conclusion drawn on a wrong or stale build is
worthless.

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
opengate_tests -t geometry/test001_g4geometry_geometrymapping.py   # or any geometry test
# the run header must print: Geant4 version is OK
```

If it prints `Geant4 version is not ok`, or a `PhysicsListBuilder registry differs…` warning,
stop and fix the environment (`../environment-setup/SKILL.md` §3.3, §4.6) before touching the
geometry.

## 2. Where geometry lives in this repo

| Concern | Location |
| --- | --- |
| Volume tree, placement, repetition, regions | `opengate/geometry/volumes.py` (`VolumeBase` and subclasses) |
| Solids (shapes) | `opengate/geometry/solids.py` (`SolidBase` + one class per shape) |
| Materials and HU/voxel material tables | `opengate/geometry/materials.py` |
| Electromagnetic fields attached to volumes | `opengate/geometry/fields.py` |
| Geometry helpers | `opengate/geometry/utility.py`, `volume_info.py` |
| User-facing manager / checks | `VolumeManager` in `opengate/managers.py` |
| C++ side (G4 helpers, unique volume IDs, voxelizer) | `core/opengate_core/opengate_lib/GateGeometry*, GateUniqueVolumeID*, GateVolumeVoxelizer*` |
| User docs | `docs/source/user_guide/user_guide_reference_volumes.rst`, `…_fields.rst` |
| Tests | `opengate/tests/src/geometry/` |

**Read `user_info_defaults` of the class you are using rather than guessing a parameter name.**
Every geometry object declares its parameters there (name, doc, default, setter hook); that dict
is the authoritative API, and it is also what serialisation writes to JSON.

## 3. The volume model — define the tree in your head before coding

A GATE 10 geometry is a **tree of `VolumeBase` objects**, each with a mother. The pieces:

- **World volume** — created automatically by `gate.Simulation()`; everything must descend from
  it. A volume whose `mother` does not resolve is a fatal error, not a warning.
- **Solids** are *shapes*, not volumes: one `SolidBase` can back several volumes; a volume can
  also be a boolean compound (`BooleanSolid`, built from `creator_volumes`).
- **Placement** is `translation` + `rotation` **relative to the mother**, each of which may be a
  *list* — the list length is what **repeats** the volume (there is no separate `repeater`
  parameter). Keep the two lists consistent in length; a mismatch silently misplaces daughters.
- **Regions** — named sets of volumes used by cuts, stepping and biasing. Cuts and production
  thresholds are set per region, so how you group volumes into regions is a physics decision
  (see [`geant4-physics-expert.md`](geant4-physics-expert.md) §4).

When you add a volume, always write down: mother, material, solid, placement, and (if any) the
region it belongs to. A missing entry in that list is the most common geometry mistake.

## 4. Choosing and defining a solid

Shapes available in `opengate/geometry/solids.py` (grep the file — do not invent a class name):

`BoxSolid`, `SphereSolid`, `EllipsoidSolid`, `TubsSolid`, `ConsSolid`, `PolyhedraSolid`,
`HexagonSolid`, `TrdSolid`, `TrapSolid`, `TesselatedSolid`, `ImageSolid`, `BooleanSolid`.

Rules that pay off:

- **Choose the simplest shape that respects the physics.** A box approximation of a curved
  detector changes attenuation and scatter paths; it is a modelling decision, not a shortcut.
- **Use `TesselatedSolid` for STL/arbitrary surfaces** and `ImageSolid` for voxelised images —
  both are much heavier than primitives, so reserve them for shapes you cannot express
  analytically. Voxelised geometries also cost memory proportional to the image size.
- **Prefer a boolean compound over hand-placed subtraction volumes** when a shape is a
  difference/intersection — `BooleanSolid` is built through the G4 boolean solids and keeps the
  intent explicit.
- GATE 10 lengths/angles are numbers **with units** (`gate.g4_units.mm`, `.cm`, `.deg`, …).
  Mixing a bare number where a length is expected is a silent scale error (§7).

## 5. Materials

- Material names are **Geant4 NIST names** (`"G4_WATER"`, `"G4_AIR"`, `"G4_LEAD"`, …) unless you
  define your own. Confirm a NIST name exists before using it — grep `core/` / the docs rather
  than recalling it.
- Custom materials and elements are declared through the material database in
  `opengate/geometry/materials.py` and the manager; a volume referencing an undefined material
  fails at initialization.
- For CT-like phantoms use the **HU / voxel material** machinery (`read_voxel_materials`,
  `HU_read_materials_table`, `HU_read_density_table`, `HU_linear_interpolate_densities`): an
  image gives a per-voxel material, and the HU↔density conversion is a *modelling choice* with
  dosimetry consequences. State the table you used and the interpolation.
- Density and composition errors are invisible in a successful run. If a result looks off by a
  constant factor, check the material density before re-checking the physics.

## 6. Repetition, placement and the volume tree

- **Repeated volumes** come from a *list* of translations and/or rotations. The count is the
  number of placements; `number_of_repetitions` is derived, not set by hand.
- **The tree is updated lazily.** Mutating a volume's mother/placement after creation marks the
  tree dirty (`_request_volume_tree_update`) — read `volume_manager` state rather than a stale
  cached reference. Adding a child after reading `children_volumes` can read a pre-update tree.
- **Unique volume IDs** (`GateUniqueVolumeID`) identify a placement; actors that score per
  volume use them. Two volumes with the same name in different mothers are distinct IDs — do not
  assume the *name* is unique.
- Keep names meaningful: they appear in actor output, logs and error messages, and renaming one
  breaks any test or script that addressed it.

## 7. Geometry is a silent-failure risk — check these explicitly

Geometry bugs rarely raise; they change the numbers.

1. **Overlaps and "daughter outside mother".** Enable the Geant4 geometry checks and *read* the
   output; do not silence overlaps. Overlaps change track lengths, energy deposition and
   coincidence rates while the simulation still runs to completion.
2. **Units.** A length in the wrong unit (mm vs cm) scales the whole geometry. Sanity-check one
   known dimension against its physical value.
3. **Placement sign / axis.** A misplaced detector sees the wrong solid angle. Verify the
   expected count rate changes in the direction you predicted, not just "it changed".
4. **Mother/attachment mismatch.** A scorer or source attached to a volume that does not contain
   the particles produces zero, not an error.
5. **Voxelised image alignment.** Index-to-world mapping (origin, spacing, orientation) is easy
   to get subtly wrong; assert on a few known voxels.
6. **Boolean/compound correctness.** A compound with a rotated/translated creator volume builds
   without error but is not the shape you drew.

See §9 for how to turn the first ones into assertions instead of eyeballing.

## 8. Geometry vs. physics vs. scoring — keep the boundary clear

- A geometry change that alters attenuation/scatter/solid angle is a **physics** decision: state
  the expected effect before looking at the output, and justify it against
  [`geant4-physics-expert.md`](geant4-physics-expert.md).
- Cuts and regions are shared between geometry and physics: the region a volume belongs to
  determines its production thresholds. Changing the grouping changes the physics.
- If a scorer reads zero, first confirm the *geometry* puts the volume where you think (a quick
  visualisation or a bounding-box print), then look at the actor.

## 9. Visualise rather than assume

The fastest geometry check is to look at the model. GATE 10 can render the geometry
(`opengate_visu`, and volume `color`/`style` user parameters: `style` is `default`/`solid`/
`wireframe`). Rendering requires Qt-enabled Geant4; if the environment was built without it,
that is an environment limitation, not a reason to skip the check — fall back to printing
bounding boxes (`SolidBase.bounding_limits`, `bounding_box_size`) and asserting on them.

## 10. Definition of done

- [ ] Environment proven correct (Geant4 version OK); no stale-`.so` warning.
- [ ] Mother, material, solid, placement and region stated for every volume you added.
- [ ] Solid is the simplest shape that respects the physics; heavy shapes justified.
- [ ] Units explicit on every length/angle; one known dimension sanity-checked.
- [ ] Tree state read after mutation, not from a stale cached reference.
- [ ] Geometry checks run and their output read — no ignored overlaps.
- [ ] Material names/densities verified (NIST name exists, or the custom definition is correct).
- [ ] Voxelised/boolean geometry asserted on known voxels/features, not just "it ran".
- [ ] Any resulting physics change justified and, if it is a test, tolerance explained
      (see [`test-writer.md`](test-writer.md)).
