# Skill: `engineering/gate-physics-expert`

**Role:** decide and verify the *GATE 10 physics layer* — the physics manager, how **sources**
inject primaries, and how **actors** turn the resulting Geant4 tracks into scored quantities.

[`geant4-physics-expert.md`](geant4-physics-expert.md) owns the *Geant4* physics (lists, EM
models, cross-sections, decay data). This skill owns the GATE layer that configures and exploits
them: `PhysicsManager`, `SourceManager`/sources, `ActorManager`/actors, filters and biasing.
Read the Geant4 skill for the underlying physics; read this one for the GATE machinery built
on top of it.

---

## 1. Establish the environment before discussing physics

Physics conclusions are worthless on a wrong build. Confirm **both**:

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
opengate_tests -t actors/test008_dose_actor.py        # run header must print: Geant4 version is OK
python -c "from opengate_core import GateInfo; print(GateInfo.get_G4Version())"
```

GATE pins Geant4 `v11.4.2`. A `Geant4 version is not ok` line, or a
`PhysicsListBuilder registry differs from the linked Geant4` warning, means the environment — not
the physics — is wrong: fix it (`../environment-setup/SKILL.md` §3.3, §4.6) before interpreting
any result.

## 2. Where the GATE physics layer lives

| Concern | Location |
| --- | --- |
| Physics lists, EM extensions, cuts, `PhysicsManager` | `opengate/physics.py` + `PhysicsManager` in `opengate/managers.py` |
| Sources (primaries) | `opengate/sources/**` (`generic.py`, `phspsources.py`, `voxelsources.py`, `gansources.py`, `beamsources.py`, `phidsources.py`, `lastvertexsources.py`) |
| Actors (scoring) | `opengate/actors/**` (`doseactors.py`, `digitizers.py`, `phspactors.py`, `arbitraryactors.py`, `biasingactors.py`, `coincidences.py`, `chemistryactors.py`) |
| Filters (track-level selection) | `opengate/actors/filters.py` |
| Actor output plumbing | `opengate/actors/actoroutput.py`, `dataitems.py` |
| C++ side | `core/opengate_core/opengate_lib/` (`GateSourceManager`, physics builder, `Gate…Actor` classes) |
| User docs | `docs/source/user_guide/user_guide_physics.rst`, `…_reference_actors.rst`, `…_reference_sources*.rst`, `…_reference_filters.rst` |
| Tests | `opengate/tests/src/physics/`, `…/source/`, `…/actors/`, `…/chemistry/` |

**Read `user_info_defaults` of the object you are using** rather than guessing a parameter name —
that dict is the authoritative API and what gets serialised.

## 3. Physics lists — the reasoning you must write down

`opengate/physics.py` builds the available list names from
`reference_physics_list_base_class_names` + `reference_physics_list_em_extensions` +
`reference_physics_list_special_builders` (`_build_available_reference_physics_list_names`).
**Read that function**; never guess a name.

For any change or recommendation, state:

1. **The particles and energies involved** — this drives the valid list.
2. **The required EM accuracy** (e.g. low-energy EM models for < ~1 keV photons/electrons in
   hadron therapy or microdosimetry).
3. **The list you picked and the list you rejected**, with the reason.
4. **The cost** — accuracy vs. runtime, and whether the change invalidates prior results.

Verify the list is *actually* in effect, not just that the parameter name was accepted:

- check the resolved list in the run output / `opengate_info`;
- confirm the linked Geant4 provides it — the `PhysicsListBuilder registry differs…` warning means
  a registered list has no C++ binding (a stale build, B-001).

## 4. Sources — the GATE layer that injects primaries

A source defines **what, where, when and how many** primaries enter the simulation. Getting the
source wrong is the most common reason a correct detector model gives wrong absolute numbers.

- **Every source is a `SourceBase`** (`opengate/sources/base.py`) with common parameters:
  `attached_to` (the volume it is attached to — `mother` is **deprecated**), `start_time` /
  `end_time`, and the **mutually exclusive** `number_of_primaries` vs. `activity`
  (`n` is deprecated → `number_of_primaries`).
- **Absolute normalisation**: a result is only comparable to literature if the source
  normalisation is known — per history? per Bq? per primary? State it, and check that
  `activity`/`number_of_primaries` (with `half_life` where relevant) give the history count you
  expect.
- **Key source types** (grep `opengate/sources/` for the current set):
  `GenericSource` (particle + energy + position + direction), `VoxelSource`,
  `VoxelizedPromptGammaTLESource`, `PhaseSpaceSource`, `GANSource`/`GANPairsSource`,
  `IonPencilBeamSource`, `TreatmentPlanPBSource`, `PhotonFromIonDecaySource`, `LastVertexSource`,
  `DebugSource`.
- **The generic source has three validated blocks** — position, direction, energy:
  - position types include `point`, `sphere`, `box`, `disc`, `cylinder`, `surface_sphere`;
  - direction types include `iso`, `histogram`, `momentum`, `focused`, `beam2d`, `cos`;
  - energy types include `mono`, `discrete`, `histogram`, `interpolated`.
  These are enforced by `PositionValidator` / `DirectionValidator` / `EnergyValidator` in
  `opengate/sources/generic.py` — read the validator to see exactly what is accepted rather than
  guessing a keyword.
- **A source attached to the wrong volume produces zero primaries, not an error.** Attach to a
  volume that actually contains the emission region.
- **TLE / prompt-gamma and phase-space sources** carry their own physics subtleties (rejection
  sampling, weights); a weighted source changes how you must normalise the result.
- Randomness is controlled by `sim.random_seed` (`"auto"` or an integer); log the resolved
  `current_random_seed` when reporting a result.

## 5. Actors — the GATE layer that turns tracks into numbers

Actors attach scoring to volumes. Two families:

- **Dose / deposit actors** (`opengate/actors/doseactors.py`): `DoseActor`, `TLEDoseActor`,
  `LETActor`, `BeamQualityActor`, `REActor`, `RBEActor`, `ProductionAndStoppingActor`,
  `FluenceActor`, `EmCalculatorActor`. These score per voxel and write images; the
  voxelisation, `size`/`spacing`/`origin`, and the scorer's volume are the things that go wrong.
- **Digitizers / coincidence / phase space** (`opengate/actors/digitizers.py`):
  `DigitizerAdderActor`, `DigitizerReadoutActor`, `DigitizerBlurringActor`,
  `DigitizerSpatialBlurringActor`, `DigitizerEfficiencyActor`, `DigitizerEnergyWindowsActor`,
  `DigitizerDeadTimeActor`, `DigitizerPileupActor`, `DigitizerHitsCollectionActor`,
  `DigitizerProjectionActor`, `CoincidenceSorterActor`, `PhaseSpaceActor`.

Rules that prevent most actor mistakes:

- **Score into the volume that sees the particles.** An actor attached to a volume the tracks do
  not enter writes zeros, silently.
- **Filters and attributes select *what* is scored**: `opengate/actors/filters.py` (particle,
  energy, process, volume, …) and the `*InVolumeAttribute` classes let you restrict scoring to
  specific tracks/steps. A missing filter changes the quantity you think you measured.
- **Know the units and the normalisation of every actor output** before comparing to literature —
  dose per history vs. per Bq, energy vs. dose, per-voxel vs. total.
- **Digitizers are for detector response**: blurring, dead time, efficiency and energy windows
  model the readout. Dead time and pile-up are *rate-dependent* — their effect changes with
  activity, so test them at the rates you care about.
- **Never invent a binding.** A `Gate…Actor` class must exist in `core/` **and** in the rebuilt
  `.so`; a missing one means a stale build (`../environment-setup/SKILL.md` §4.6).

## 6. Cuts, regions and biasing

- Cuts are **range-based, per region**, expressed in the simulation's units; a global cut plus
  per-volume overrides is normal. A wrong cut is a **silent** physics error — the run succeeds and
  the numbers look plausible.
- When you change a cut, **re-derive the expected effect** (e.g. dose in a thin layer) *before*
  looking at the output, so you can distinguish "changed as expected" from "changed otherwise".
- Assert on the cut Geant4 actually adopted, not the value you set.
- Biasing (`opengate/actors/biasingactors.py`, `GateAcceptanceAngle*`) changes the sampling: a
  biased run's **weights** must be applied to get a physical result. Un-weighted biased output is
  wrong by construction.

## 7. Statistics — the most common physics mistake

Simulation output is stochastic; a number without an uncertainty is not a result.

- Never compare two runs on a difference smaller than their combined statistical uncertainty.
- Justify tolerances from the **statistics**, not to make a test pass: the relative sigma of a
  scored quantity scales roughly as `1/sqrt(N)` histories.
- **Vary the seed** before believing a difference; a change that reproduces with one seed only is
  noise.
- Prefer scoring more histories once over repeating a low-statistics run many times.

## 8. Physics-sensitive things worth checking explicitly

- **Decay / half-life / branching ratios** — a wrong ion or decay setting gives a plausible but
  wrong spectrum.
- **Energy-spectrum endpoints** — compare against the analytically expected endpoint.
- **Attenuation** — a mono-energetic beam through a known thickness should follow the expected
  exponential within statistics.
- **Absolute normalisation** — units, per-what normalisation, and source activity vs. histories.
- **Coincidence / timing** — time windows, dead time and sorter settings change the coincidence
  rate; check the count against the expected geometric/activity scaling.

## 9. Definition of done

- [ ] Environment proven correct; linked Geant4 matches the pin; no registry warning.
- [ ] Physics list justified in writing (chosen **and** rejected alternatives).
- [ ] Source: type, attachment volume, position/direction/energy, and **normalisation** stated.
- [ ] Actor: attached to the right volume, filters/attributes intentional, output units and
      normalisation stated.
- [ ] Cuts re-derived and asserted on the value Geant4 adopted; biasing weights accounted for.
- [ ] Result reported with its statistical uncertainty and the resolved seed.
- [ ] Conclusion replicated with at least one other seed when it rests on a small difference.
- [ ] Any test asserting on physics quantities has a justified tolerance
      (see [`test-writer.md`](test-writer.md)).
