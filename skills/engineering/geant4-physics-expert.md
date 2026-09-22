# Skill: `engineering/geant4-physics-expert`

**Role:** decide and verify the *physics* of a GATE 10 simulation — physics lists, production
cuts, EM options, decay/transport, and the statistical realism of the result.

This skill is about physics correctness, not about code structure. For code, see
[`python-gate-developer.md`](python-gate-developer.md); for failing simulations, see
[`simulation-debugger.md`](simulation-debugger.md).

---

## 1. Establish the environment before discussing physics

Physics conclusions are worthless on a wrong build. Confirm **both**:

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
opengate_tests -l 2>&1 | head -5     # must print: Geant4 version is OK
python -c "from opengate_core import GateInfo; print(GateInfo.get_G4Version())"
```

The project pins Geant4 `v11.4.2`. *Do not* reason about cross-section or EM-model behaviour
on a different Geant4 patch level — that is exactly the mistake that made two geometry tests
look like bugs (B-004/B-009).

## 2. Where physics lives in this repo

| Concern | Location |
| --- | --- |
| Physics lists (names, modular/augmented classes) | `opengate/physics.py` |
| EM extensions / aliases | `reference_physics_list_em_extensions`, `…_aliases` in `opengate/physics.py` |
| C++ physics binding | `core/opengate_core/opengate_lib/` (physics builder) |
| User documentation | `docs/source/user_guide/` (physics pages) + the reference pages |
| Tests that assert on physics | `opengate/tests/src/physics/`, plus `source/` and `chemistry/` |

`opengate/physics.py` builds its available-physics-list names from
`reference_physics_list_base_class_names` + EM suffixes + special builders
(`_build_available_reference_physics_list_names`). **Read that function** rather than guessing
a list name, and never invent a Geant4 class name — grep `core/` for the wrapper first.

## 3. Choosing a physics list — the reasoning you must write down

Physics-list choice is a modelling decision with dosimetry consequences. For any change or
recommendation, state:

1. **The particles and energies involved** (this drives the valid list).
2. **The required EM accuracy** (e.g. low-energy EM models for < ~1 keV photons/electrons,
   in hadron-therapy or microdosimetry contexts).
3. **The list you picked, and the list you rejected**, with the reason.
4. **What it costs** — accuracy vs. runtime, and whether the change invalidates prior results.

Verify the list is actually in effect rather than trusting the parameter name:

- check the resolved name in the simulation output / `opengate_info`;
- confirm the linked Geant4 provides it — the runner warns with
  `PhysicsListBuilder registry differs from the linked Geant4` when a registered list has no
  C++ binding (this warning appeared on a stale build: B-001).

## 4. Production cuts and thresholds

- Cuts are range-based, expressed in the simulation's units, and are applied per region —
  a global cut plus per-volume overrides is normal.
- A cut that is wrong for a region is a silent physics error: the simulation runs and the
  numbers look plausible.
- When you change a cut, re-derive the *expected* effect (e.g. dose in a thin layer) before
  looking at the output, so you can tell "changed as expected" from "changed for another
  reason".
- Assert on the cut that Geant4 actually adopted, not on the value you set.

## 5. Statistics: the most common physics mistake

Simulation output is stochastic. A result is only meaningful with its uncertainty.

- Never compare two runs on a difference smaller than their statistical uncertainty.
- Justify tolerances from the *statistics*, not to make a test pass: for N histories the
  relative sigma of a scored quantity scales roughly as `1/sqrt(N)`.
- Vary the seed before believing a difference. A change that only reproduces with one seed is
  noise.
- Prefer scoring more histories once over repeating a low-statistics run many times.
- `sim.random_seed` accepts `"auto"` or an explicit integer; `current_random_seed` records the
  concrete seed resolved for the run (`opengate/managers.py`). Log it when reporting a result
  so the run is reproducible.

## 6. Physics-sensitive things worth checking explicitly

- **Decay / half-life and branching ratios** — a source with the wrong ion or decay settings
  produces a plausible-looking but wrong spectrum.
- **Energy spectrum endpoints** — compare against the analytically expected endpoint.
- **Attenuation** — a mono-energetic beam through a known thickness should follow the
  expected exponential to within the statistics.
- **Dose normalisation** — check the units and the normalisation (per history? per Bq? per
  primary?) before comparing to literature values.

## 7. Definition of done

- [ ] Environment proven correct; Geant4 version matches the pin.
- [ ] Physics list justified in writing (chosen **and** rejected alternatives).
- [ ] Cuts re-derived, and asserted on the value Geant4 adopted.
- [ ] Result reported with its statistical uncertainty and the resolved seed.
- [ ] Conclusion replicated with at least one other seed when it rests on a small difference.
- [ ] Any test asserting on physics quantities has a justified tolerance
      (see [`test-writer.md`](test-writer.md)).