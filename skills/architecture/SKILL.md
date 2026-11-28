# Skill: architecture

**Goal:** add or modify an engine, manager, actor, source, filter or physics list
without violating the GATE 10 object lifecycle.

`DesignGuidelines.md` at the repo root is marked **OBSOLETE** — do not rely on it as
documentation of the current design. Read the code in `opengate/` and the developer
guide pages under `docs/source/developer_guide/`.

---

## 1. Mental model

```
Simulation (opengate/managers.py)          <- the user-facing object
 ├── VolumeManager, PhysicsManager, SourceManager, ActorManager, ...   (user input + checks)
 ├── Engines  (opengate/engines.py)                                    <- build/run Geant4
 └── GateObjects (opengate/base.py)                                    <- serialisable units
        ├── Actors   (opengate/actors/**)
        ├── Sources  (opengate/sources/**)
        ├── Volumes  (opengate/geometry/**)
        └── Fields, Filters, Phantom, ...
```

Two phases:

1. **User phase** — managers receive and validate user input; nothing Geant4 is created.
2. **Initialization / simulation phase** — engines build the Geant4 world and objects
   are initialized.

**Managers check the user input; engines may assume it is valid.** Do not put user-input
validation in an engine, and do not create Geant4 objects during the user phase.

## 2. Key files (go here first)

| File | Role |
| --- | --- |
| `opengate/managers.py` | `Simulation` + all managers. Almost every user feature starts here. |
| `opengate/engines.py` | Run/init orchestration, subprocess handling, Geant4 bootstrap. |
| `opengate/base.py` | Base classes: `GateObject`, `UserElement`, `ActorBase`, deprecation helpers. |
| `opengate/actors/**` | Actors: `doseactors.py`, `digitizers.py`, `phspactors.py` (phase space), `arbitraryactors.py`, `filters.py`, `biasingactors.py`, `chemistryactors.py`, `coincidences.py`. |
| `opengate/sources/**` | `generic.py`, `phspsources.py`, `gansources.py`, `voxelsources.py`, `beamsources.py`, `phidsources.py`. |
| `opengate/geometry/**` | `volumes.py`, `solids.py`, `materials.py`, `fields.py`, `utility.py`. |
| `opengate/physics.py` | Physics lists and physics settings. |
| `opengate/userhooks.py`, `opengate/actions.py` | Where user hooks / G4 actions are registered. |
| `opengate/serialization.py`, `opengate/utility.py` | Serialisation (subprocesses!) and shared helpers. |
| `opengate_core` (C++, `core/`) | The Geant4-facing classes (`g4.GateXxx`). |

## 3. Adding an actor — the mandatory class structure

Per `docs/source/developer_guide/developer_guide_how_to_implement.rst`, an actor must:

1. **Inherit the Python base class first, then the C++ base class**:

   ```python
   class SimulationStatisticsActor(ActorBase, g4.GateSimulationStatisticsActor):
       ...
   ```

   Never the reverse order.

2. **Reference the superclass explicitly — do not** use `super()`, it cannot resolve
   the C++ base class:

   ```python
   ActorBase.initialize(self)
   ```

3. **Implement `initialize()`** calling, at minimum:

   ```python
   def initialize(self):
       ActorBase.initialize(self)
       # user-input sanity checks here, if any
       self.InitializeUserInfo(self.user_info)
       self.InitializeCpp()
   ```

4. **Implement `__initcpp__()`** and call the C++ constructor **there**, never in
   `__init__()`:

   ```python
   def __initcpp__(self):
       g4.GateSimulationStatisticsActor.__init__(self, self.user_info)
       self.AddActions({"StartSimulationAction", "EndSimulationAction"})
   ```

   Rationale: the multiprocessing mechanism de-/serialises objects, and
   `__setstate__()` in `opengate/actors/base.py` relies on `__initcpp__` to rebuild the
   C++ side in the subprocess.

5. Constructor takes **no mandatory argument except the name**, and parameters are set
   explicitly afterwards (this is also what makes dummy objects easy to build).

6. Register the actor with the actor manager, expose the user-facing class in the
   package namespace, and add tests (`skills/running-tests`) and docs
   (`skills/documentation`).

## 4. Adding a source

Same pattern as actors, with `SourceBase` + the corresponding `g4.GateXxxSource`. Sources
live in `opengate/sources/`; the user-facing creation goes through the source manager in
`opengate/managers.py`. Respect the "no mandatory `__init__` args" rule, and keep
randomness/seed handling consistent with the existing sources.

## 5. Managers and engines

- Registries are **dicts of the form `{name: object}`**, not lists — adding objects must
  not change insertion-order semantics that other code depends on.
- Manager methods validate types/sizes/ranges and raise the project exceptions
  (`opengate/exception.py`, `fatal`), with messages that name the offending parameter.
- Engines construct the Geant4 objects during initialization; they are not meant for
  user interaction and should not hold user-facing parameters.
- If you add a new engine step, wire it into the ordered initialization in
  `opengate/engines.py` and make sure subprocess/threading paths still work
  (`-p mp` in the test runner exercises them).

## 6. Physics

Physics lists and cuts live in `opengate/physics.py` and the C++ side. When adding a
physics list: register it on both sides, expose its name for the user, and add a test
asserting that the expected processes/particles exist rather than only that the
simulation runs (see `docs/source/developer_guide/developer_guide_physics.rst`).
Do not invent Geant4 class names — grep `core/` for the existing wrapper.

## 7. Serialisation, multiprocessing, subprocesses

- Anything added to a Gate object becomes part of its serialised state; keep it
  JSON-friendly (see `opengate/jsonpickle` usage and `opengate/serialization.py`).
- Non-serialisable runtime state (Geant4 pointers) must be recreated in `__initcpp__`.
- Always run at least one test in `-p mp` mode when touching objects or engines.

## 8. Checklist for a new object type

- [ ] Python base class first, C++ base second; explicit super-calls, no `super()`.
- [ ] `__initcpp__()` used for the C++ constructor and `AddActions(...)`.
- [ ] `initialize()` calls `InitializeUserInfo` and `InitializeCpp` in the right order.
- [ ] Registered in the right manager; user-facing name exposed.
- [ ] User input validated in the manager, not the engine.
- [ ] Serialisation round-trip works under `opengate_tests -p mp`.
- [ ] Test added under `opengate/tests/src/<subdir>/testNNN_*.py`.
- [ ] User + developer doc page updated (`skills/documentation`).
- [ ] `pre-commit` clean (`skills/code-style`).