# Skill: `engineering/gate-chemistry-expert`

**Role:** configure and verify the *GATE 10 chemistry layer* — Geant4-DNA chemistry lists, the
track-structure EM region that chemistry requires, the chemistry world (background components and
scavenger reactions), and the chemistry actors and counters that score species and reactions.

This is the chemistry sibling of [`gate-physics-expert.md`](gate-physics-expert.md). It owns the
GATE configuration layer for Geant4-DNA chemistry; read the physics skill for the general physics
list / source / actor machinery, and [`geant4-physics-expert.md`](geant4-physics-expert.md) for the
EM-model reasoning underneath. Read this skill whenever you touch `sim.chemistry_manager`,
`opengate/chemistry.py`, `opengate/actors/chemistryactors.py` or
`opengate/actors/chemistrycounters.py`.

> **Alpha-stage feature.** The code itself says so (`ChemistryManager.alpha_warning_message` in
> `opengate/managers.py`, and the warning at the top of `docs/source/user_guide/user_guide_chemistry.rst`):
> interfaces, behavior and outputs may still change and must be validated before production use.
> Never present a chemistry result as validated, and expect the API to move.

---

## 1. Establish the environment first

Chemistry conclusions on a wrong build are worthless, and chemistry is more sensitive to a stale
build than most of GATE because it depends on Geant4-DNA chemistry lists and the
`GateVChemistryActor` / `GateTimeStepAction` C++ bridges being present in the rebuilt `.so`.

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
opengate_tests -t chemistry/test101_chemical_counting_actor.py
# the run header must print: Geant4 version is OK
```

If `Geant4 version is not ok` appears, or an import of a `G4EmDNAChemistry*` class fails with
`is not bound in opengate_core`, stop — that is a stale/incomplete build, not a chemistry problem
(`../environment-setup/SKILL.md` §3.3, `../environment-setup/geant4-itk.md` §7). A `Chemistry list '<name>' is not bound in
opengate_core` fatal is raised by `ChemistryList.initialize_before_runmanager`, and it means the
same thing.

## 2. Where chemistry lives in this repo

| Concern                                             | Location                                                                        |
| --------------------------------------------------- | ------------------------------------------------------------------------------- |
| Chemistry list, world, species/reactions/dissociations | `opengate/chemistry.py`                                                       |
| Chemistry-aware actors + their outputs              | `opengate/actors/chemistryactors.py`                                            |
| Counters (built-in and configured)                  | `opengate/actors/chemistrycounters.py`                                          |
| `ChemistryManager` (user-facing)                    | `opengate/managers.py`                                                          |
| Chemistry engine (lifecycle wiring)                 | `ChemistryEngine` in `opengate/engines.py`                                      |
| Physics-list forwarding for chemistry               | `opengate/physics.py` (`g4_augmented_physics_list`, `set_chemistry_list`)       |
| C++ side                                            | `core/opengate_core/opengate_lib/` (`GateVChemistryActor`, `GateChemicalCountingActor`, `GateTimeStepAction`, `GateITTrackingInteractivity`, `GateChemistryController`) |
| User docs                                           | `docs/source/user_guide/user_guide_chemistry.rst`                               |
| Developer docs                                      | `docs/source/developer_guide/developer_guide_chemistry_architecture.rst`        |
| Tests                                               | `opengate/tests/src/chemistry/`                                                 |

**Read `user_info_defaults` of the object you configure** rather than guessing a parameter name —
it is the authoritative API and what gets serialised. The chemistry architecture is described at
length in `developer_guide_chemistry_architecture.rst`; read it before changing the wiring rather
than rediscovering the lifecycle from the code.

## 3. The three ingredients chemistry always needs

Chemistry is **not** enabled by one switch. A working chemistry simulation needs all three, and
omitting one gives a silently chemistry-free run:

1. **A standard physics list** — `sim.physics_manager.physics_list_name` (e.g.
   `"G4EmStandardPhysics"`). The chemistry list is attached to an *augmented* physics list
   (`g4_augmented_physics_list`) so its `ConstructParticle`/`ConstructProcess` are forwarded; you do
   not build that yourself.
2. **A Geant4 chemistry list** — `sim.chemistry_manager.chemistry_list_name`, one of
   `known_g4_chemistry_list_names` in `opengate/chemistry.py`: `G4EmDNAChemistry`,
   `G4EmDNAChemistry_option1`, `…_option2`, `…_option3`. `"default"` resolves to the manager's
   default via a setter hook; left `None`, chemistry stays off unless an actor explicitly requests
   it. **Read `known_g4_chemistry_list_names`; do not invent a name.**
3. **Track-structure EM physics in the region of interest** — chemistry needs Geant4-DNA
   track-structure EM where the radicals are produced. Configure it per region/volume, not
   globally:
   - `volume.set_track_structure_em_physics("G4EmDNAPhysics_option2")` (the usual way), or
   - `sim.physics_manager.set_track_structure_em_physics(volume_name, …)` /
     `…_in_region(region_name, …)`, or
   - let a chemistry actor request it (see §6).

   A **global** track-structure EM setting is refused: `PhysicsManager` tells you to configure it
   "only per region" (`opengate/managers.py`).

Two actors requesting **different** track-structure EM for the **same** volume is a `fatal`
(`PhysicsManager` conflict check), so make the requests agree.

`sim.chemistry_manager.time_step_model` selects the Geant4 chemistry time-step model:
`"SBS"` (default), `"IRT"`, or `"IRT_syn"` — the allowed values are enforced by the parameter.
Chemistry regions are also where the `G4EmDNAPhysics*` track-structure cut/step behaviour lives, so
a chemistry result is meaningless if the region is wrong.

## 4. Customising the chemistry list

`sim.chemistry_manager.chemistry_list` is a `ChemistryList` that **wraps one built-in Geant4
chemistry list and appends to it** (it registers itself as the active chemistry list, having
deregistered the built-in object used only as a callback provider).

- **Species** — `chem_list.add_chemical_species(name=…, definition_name=…, molecular_mass=…,
  charge=…, electronic_level=…, diffusion_radius=…, diffusion_coefficient=…)`, or pass a
  `ChemicalSpecies`. `definition_name` defaults to `name`. A species that already exists in the
  molecule table has its properties *updated* rather than duplicated.
- **Bimolecular reactions** — `chem_list.add_reaction(reactant_a=…, reactant_b=…,
  rate_constant=…, products=[…], reaction_type=…)`. `rate_constant` is a genuine `float` in
  Geant4-DNA units (**M⁻¹ s⁻¹**, i.e. `dm³ mol⁻¹ s⁻¹`); `reaction_type` is `0` (totally
  diffusion-controlled) or `1` (partially diffusion-controlled). **`H2O` is the implicit solvent
  and is silently *not* added as an explicit reaction product** — do not "fix" that by adding it
  again. `reactant_a`/`reactant_b` are **sorted** internally, so the reaction key is
  order-independent.
- **Unimolecular dissociations** — `chem_list.add_chemical_dissociation(parent=…, products=[…],
  probability=…, energy=…)`, or a `ChemicalDissociation`.
- **Customisation without a base list is a `fatal`**: if you add species/reactions/dissociations
  you must have resolved a `chemistry_list_name` first (`ChemistryList.initialize_before_runmanager`,
  `has_customizations()`).

Duplicates are `fatal` rather than ignored: adding the same species name, the same reaction key or
the same dissociation twice stops the run — which is what you want, but it means an inherited
default list plus your additions can collide.

## 5. The chemistry world: background components and scavengers

The chemistry world is an **optional** box that defines the chemical background and scavenger
reactions. It is separate from the geometry volume tree.

- Create it with `sim.chemistry_manager.create_chemistry_world(...)`, passing **either** a
  `volume=` **or** the pair `translation=`/`half_size=` — never both, never neither (both are
  `fatal`). **Only one chemistry world per simulation**; replacing it requires setting
  `chemistry_manager.chemistry_world = None` first.
- `set_volume()` currently accepts **only a `BoxVolume`**, with **no repetition** and an
  **axis-aligned** (identity rotation) box attached **directly to the world** — anything else is a
  `fatal` listing the offending volume. `half_size` is derived as `size / 2`.
- **Components** (the chemical background): `world.add_component(molecule_name, concentration)`
  with a **positive** concentration in the appropriate concentration unit (mol/L is the convention
  in Geant4-DNA). Duplicate species are `fatal`.
- **Scavenger reactions**: `world.add_scavenger_reaction(tracked_molecule=…, scavenger=…,
  products=[…], rate_constant=…, reaction_type=…)`. The `scavenger` **must already be a defined
  component**; the validation (`validate_scavenger_configuration`) otherwise stops the run with the
  list of known components. `rate_constant` must be non-negative.
- **`pH`** — the stock `G4DNAScavengerMaterial` expects an **integer** pH; a non-integer value is a
  `fatal` at material creation. Set it only if you need it.

Ordering matters: the scavenger material is built **after** the chemistry list has populated the
molecule table, and `G4DNAScavengerProcess` caches the material in `BuildPhysicsTable()`. The
`ChemistryEngine` handles that ordering for you — do not try to create the scavenger material by
hand before Geant4 initializes.

## 6. Chemistry actors and their configuration order

`ChemistryActorBase` (`opengate/actors/chemistryactors.py`) is the Python base; chemistry
participation itself is implemented in the C++ `GateVChemistryActor`, so the Python class is mostly
configuration, validation and actor discovery. `ActorManager.has_chemistry_actors()` and
`ActorBase.is_chemistry_actor` are what the engines use to decide chemistry is active.

The one concrete actor today is **`ChemicalCountingActor`**, a passive chemistry-scoring actor
"inspired by chem6". Its geometry-relevant parameters:

| Parameter | Meaning |
| --- | --- |
| `attached_to` | the volume whose chemistry is scored (must see the tracks) |
| `track_structure_em_physics` | DNA EM for the attached region; **defaults to `"G4EmDNAPhysics_option2"`** and can be set directly on the actor, which then requests it for the region |
| `track_only_primary` / `primary_pdg_code` | chem6-like logic restricted to the primary (default PDG 11 = e⁻) |
| `energy_loss_min` / `energy_loss_max` | kill the primary / abort the event above an accumulated energy loss (negative disables) |
| `min_kinetic_energy` | kill the primary below this kinetic energy |
| `let_cutoff` | restricted-LET cutoff; secondary energies below it are folded into the event deposit |
| `times_to_record` | explicit chemistry times at which species numbers and G-values are recorded |
| `number_of_time_bins` | if `> 0` and `times_to_record` is empty, logarithmically spaced scoring times like chem6 |

`ChemicalCountingActor` **requests DNA EM for the region it is attached to** (this is resolved before
Geant4 constructs the region; see `PhysicsManager`'s actor-request collection). If you also set
`track_structure_em_physics` on the volume, set the **same** value or the run is `fatal`.

Results land in the `results` output (`ActorOutputChemicalCountingActor`, JSON): counters such as
`recorded_events`, `chemistry_starts`, `chemistry_stages`, `pre/post_time_step_calls`,
`reaction_count`, `killed_particles`, `aborted_events`, `total_energy_deposit`,
`accumulated_primary_energy_loss`, `mean/std_restricted_let`, plus `species` and `times_to_record`.
The chemistry output currently stores **merged data only** — asking for `which != "merged"`
produces a warning and is ignored.

## 7. Counters — declarative, and the multi-threaded policy

Counters are declared on the actor via `counter_config` and exposed as actor outputs
(`ActorOutputChemicalCounter`). `chemistry_counter_types` in `opengate/actors/chemistrycounters.py`
maps the names you can pass:

- `BuiltinMoleculeCounter` — species counts, backed by `G4MoleculeCounter`. Key parameters:
  `consider_molecules` (`"all"` or a list), `ignored_molecules`, `active_lower_bound` /
  `active_upper_bound`, `time_comparer`, and the time-consistency checks. A molecule named in
  **both** `consider_molecules` and `ignored_molecules` is a `fatal`, as is an unknown molecule name
  (the message lists the known names).
- `BuiltinReactionCounter` — reaction counts, backed by `G4MoleculeReactionCounter`; same common
  time/verbose options.
- `ConfiguredReactionCounter` — counts **specific** reaction signatures given as
  `tracked_reactions` (`TrackedChemicalReaction` objects or dicts), optionally as a time series
  (`record_time_series`). It requires at least one tracked reaction and an actor exposing
  `RegisterConfiguredReactionCounter`.
- `ConfiguredSpeciesCounter` — counts **specific** species (`tracked_species`), requiring
  `RegisterConfiguredSpeciesCounter`.

`ChemicalCountingActor` deactivates `configured_reaction_counter` and `configured_species_counter`
by default and supports **at most one** molecule counter for its built-in species path (more is a
`fatal`).

**Manager policy must not conflict.** `required_molecule_counter_manager_policy` (reset before
event/run, reset master with workers, accumulate into master) is merged across all chemistry actors;
requesting the same key with two different values is a `fatal`. `ChemicalCountingActor` fixes
`reset_counters_before_event = reset_counters_before_run = True` and
`accumulate_counter_into_master = False`. If you add a chemistry actor that wants a different
policy, expect a conflict.

## 8. Confining chemistry and multi-threading

- `sim.chemistry_manager.confine_chemistry_to_volume` — when set, a single global chemistry
  controller (`GateChemistryController`) **kills chemistry tracks starting outside that volume
  subtree**. It accepts `None`, a volume name, or a volume object (anything else is a `fatal`). Use
  it to keep the chemistry stage local to the region you care about; without it chemistry runs
  across the whole world and costs time for no scoring benefit.
- Chemistry callbacks fan out through `GateTimeStepAction` and `GateITTrackingInteractivity`, which
  are registered with the chemistry actors by `ChemistryEngine.initialize_after_runmanager`. A
  chemistry actor that is not in `actor_manager.sorted_actors` (or is added after initialization)
  will not receive callbacks — add actors before `run()`.
- Chemistry plus multi-threading is the least-exercised combination; see
  `chemistry/test102_chemical_counting_actor_aggregate_mt.py`. Compare against a
  `number_of_threads = 1` run before trusting an MT count, and remember §9's statistics rules —
  thread aggregation is exactly where counter-policy conflicts surface.

## 9. Physics scrutiny for chemistry results

All of [`gate-physics-expert.md`](gate-physics-expert.md) §7 (statistics) and §8
(physics-sensitive checks) applies. Chemistry adds its own:

- **G-values / species yields** are the physical anchor: compare the number of species produced per
  unit deposited energy against published Geant4-DNA values for the same chemistry list and
  time-step model, within the statistics of your run.
- **The chemistry list *and* the option number change the result.** `G4EmDNAChemistry_option1/2/3`
  differ in their reactions and dissociations; state which one you used, and never compare results
  across options as if they were the same model.
- **The time-step model matters**: `SBS`, `IRT` and `IRT_syn` give different kinetics. Report it,
  and do not compare runs that use different models.
- **The scoring times matter**: species numbers depend on *when* they are sampled. Report
  `times_to_record` / `number_of_time_bins`, and remember `ChemicalCountingActor` builds
  logarithmically spaced times when you leave them implicit.
- **Chemistry only runs where track-structure EM is active.** A plausible-looking but empty
  chemistry output usually means the region or the confinement volume is wrong, not that "there was
  no chemistry".
- **Never compare chemistry counts on a difference below the statistical uncertainty**, and vary the
  seed (`sim.random_seed`) — chemistry populations are stochastic.

## 10. Definition of done

- [ ] Environment proven correct: `Geant4 version is OK`, chemistry lists bound in `opengate_core`,
      no stale-build warning.
- [ ] The alpha-stage status acknowledged in anything you report or document.
- [ ] All **three** ingredients present and stated: physics list, chemistry list name (exact
      `G4EmDNAChemistry*` name), track-structure EM region and model name.
- [ ] A `time_step_model` chosen deliberately and reported (`SBS` / `IRT` / `IRT_syn`).
- [ ] Every custom species/reaction/dissociation has a rate constant with correct units and an
      explicit `reaction_type`; `H2O` not re-added as an explicit product.
- [ ] If a chemistry world is used: creation mode (`volume` xor `translation`/`half_size`), every
      scavenger listed as a component, integer `pH` if any.
- [ ] Actor `attached_to` sees the tracks; the actor's `track_structure_em_physics` agrees with any
      volume/region setting (a conflict is a fatal).
- [ ] Counters intentional; the molecule-counter **manager policy** does not conflict with other
      chemistry actors.
- [ ] `confine_chemistry_to_volume` set when chemistry is only wanted locally.
- [ ] Result reported with its chemistry list option, time-step model, scoring times, seed and
      statistical uncertainty; G-values or species yields checked against expectation.
- [ ] Any test asserting on chemistry quantities has a justified tolerance
      (see [`test-writer.md`](test-writer.md)); MT result cross-checked against a single-thread run.
- [ ] Chemistry behaviour is only ever described as alpha / needs validation.
