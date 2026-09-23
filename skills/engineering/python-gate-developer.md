# Skill: `engineering/python-gate-developer`

**Role:** write and modify GATE 10 Python API code (`opengate/**`) that fits the existing
design and survives review.

Read first: [`../architecture/SKILL.md`](../architecture/SKILL.md) (object lifecycle),
[`../code-style/SKILL.md`](../code-style/SKILL.md) (formatting), and
[`../running-tests/SKILL.md`](../running-tests/SKILL.md) (how to prove it works).

---

## 1. Find the right file before writing

| You want to… | Start in |
| --- | --- |
| Add/change a user-facing object or its parameters | `opengate/managers.py` (managers own user input) |
| Add an actor | `opengate/actors/` (`doseactors.py`, `digitizers.py`, `phspactors.py`, `filters.py`, `biasingactors.py`, `arbitraryactors.py`, `coincidences.py`, `chemistryactors.py`) |
| Add a source | `opengate/sources/` (`generic.py`, `phspsources.py`, `gansources.py`, `voxelsources.py`, `beamsources.py`, `phidsources.py`) |
| Change geometry/solids/materials | `opengate/geometry/` |
| Change physics lists or cuts | `opengate/physics.py` (+ the C++ side in `core/`) |
| Change run/init orchestration | `opengate/engines.py` |
| Add a reusable helper | `opengate/utility.py` — but check it is not already there |

Never invent a new pattern when the surrounding module already has one. Pick the closest
existing class and mirror it.

## 2. Hard rules

Full mechanics and rationale: [`../architecture/SKILL.md`](../architecture/SKILL.md) §3
(actors), §7 (serialisation). These are the rules; that page shows the code.

- **No Geant4 object is created during the user phase.** Managers validate; engines build.
- **`__init__` takes no mandatory argument but the name**; parameters are set afterwards.
- **Actors: Python base class first, then the C++ base**, and call superclasses explicitly
  (`ActorBase.initialize(self)`) — `super()` cannot resolve the C++ base.
- **The C++ constructor goes in `__initcpp__()`**, never in `__init__()`; the multiprocessing
  path relies on this (`__setstate__` in `opengate/actors/base.py`).
- **Registries are `{name: object}` dicts**, not lists.
- **Validate user input in the manager**, and raise the project's own exceptions from
  `opengate/exception.py` (`fatal`) — message must name the offending parameter.
- **Heavy imports stay lazy.** matplotlib/pandas/torch are loaded on demand
  (`LazyModuleLoader` in `opengate/utility.py`); do not add a top-level heavy import on a hot
  path.
- **Library code logs, it does not print.** Use the project logger (`opengate/logger.py`),
  not `print`.
- **Everything you add becomes serialised state.** Keep it JSON-friendly
  (`opengate/serialization.py`); recreate runtime-only state in `__initcpp__`.

Formatting of all of the above is [`../code-style/SKILL.md`](../code-style/SKILL.md)'s job —
run `pre-commit` rather than matching style by eye.

## 3. Adding a user-facing parameter

1. Declare it in the owning manager's `user_info` schema (name, type, doc, default) — see the
   big `user_info` blocks in `opengate/managers.py`.
2. Attach a setter hook if the value needs validation or normalisation
   (e.g. `_setter_hook_verbose_level`).
3. Consume it during initialization, in the engine or object `initialize()`.
4. Document it (see `../../documentation/SKILL.md`) — reference page **and** the narrative
   page.
5. Add a test that *fails before your change*.

Never remove or rename a public parameter silently; check
`docs/source/user_guide/user_guide_reference_*.rst` and add a deprecation path
(`opengate/base.py` has the helpers).

## 4. Working with the C++ boundary

If your Python change needs a new binding:

- the C++ class lives under `core/opengate_core/opengate_lib/` and must be registered in
  `core/opengate_core/opengate_core.cpp`;
- **the compiled `.so` only updates when you rebuild** — an editable install does *not* pick up
  C++ changes, and the failure mode is a misleading
  `AttributeError: module 'opengate_core' has no attribute 'Gate…'`
  ([`../environment-setup/SKILL.md`](../environment-setup/SKILL.md) §4.6);
- rebuild via the **incremental** path (re-run `cmake` + `make` in `core/build/cmake.*`), not a
  full reinstall;
- build parallelism is now `os.cpu_count()`, overridable with `OPEN_GATE_BUILD_JOBS`
  (was hardcoded to 4 — B-007).

## 5. Definition of done

- [ ] Follows the closest existing module's structure; no new competing pattern.
- [ ] User input validated in the manager; project exceptions used.
- [ ] Serialisation round-trip works — verified with `opengate_tests … -p mp` (multiprocessing).
- [ ] A test exists that fails without the change and passes with it
      (see [`test-writer.md`](test-writer.md)).
- [ ] Docs updated (reference + narrative).
- [ ] `pre-commit` clean.
- [ ] You ran the relevant tests yourself; no "should work" claims.