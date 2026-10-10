# `skills/` — agent playbooks for the OpenGATE/opengate repository

Task-oriented instructions for AI agents (and humans in a hurry) working on GATE 10.
**Start with [`../AGENTS.md`](../AGENTS.md)** — it holds the repository layout, the golden
rules and the quick start. This README is the map of the skills themselves.

Each file is self-contained: read the one you need, not the whole directory.

---

## Layout

```
skills/
├── README.md                      ← this file
├── environment-setup/
│   ├── SKILL.md                   get a working dev env where ALL tests run (index)
│   ├── geant4-itk.md              build Geant4/ITK + rebuild the opengate_core extension
│   └── build-and-ci.md            packaging, releasing, CI topology, reproduce CI locally
├── running-tests/SKILL.md         the opengate_tests runner, filters, dashboard
├── code-style/SKILL.md            pre-commit / black / clang-format, conventions
├── architecture/SKILL.md          managers / engines / actors / sources lifecycle
├── documentation/SKILL.md         Sphinx pages and local build
├── engineering/
│   ├── SKILL.md                    pick a role + map of the role skills
│   ├── python-gate-developer.md    write Python API code that fits the design
│   ├── geant4-physics-expert.md    Geant4 physics: lists, EM models, cuts, statistics
│   ├── gate-physics-expert.md      GATE physics layer: sources, actors, filters
│   ├── gate-chemistry-expert.md    GATE chemistry layer: Geant4-DNA chemistry, world, counters
│   ├── geant4-geometry-expert.md   raw Geant4 geometry: solids, volumes, navigation
│   ├── gate-geometry-expert.md     GATE geometry layer: volume tree, solids, materials
│   ├── simulation-debugger.md      diagnose crashes / hangs / implausible output
│   └── test-writer.md              write tests that actually catch regressions
└── status/
    ├── task-list.md               shared work list (id, status, area, evidence)
    ├── found-bugs.md              bug log: repository bugs vs environment issues
    └── project-status.md          dated snapshot of the project and its health
```

## Which skill do I need?

| Situation | Read |
| --- | --- |
| No environment yet, or "tests fail for no reason" | [`environment-setup/SKILL.md`](environment-setup/SKILL.md) |
| Need to run, filter, or interpret tests | [`running-tests/SKILL.md`](running-tests/SKILL.md) |
| **Releasing**, changing packaging/wheels, or editing `.github/workflows/` | [`environment-setup/build-and-ci.md`](environment-setup/build-and-ci.md) |
| **Building Geant4/ITK or the `core/` C++ extension** | [`environment-setup/geant4-itk.md`](environment-setup/geant4-itk.md) |
| About to commit | [`code-style/SKILL.md`](code-style/SKILL.md) |
| Adding an actor / source / engine / manager | [`architecture/SKILL.md`](architecture/SKILL.md) |
| Adding or changing a docs page | [`documentation/SKILL.md`](documentation/SKILL.md) |
| Writing or refactoring `opengate/**` Python code | [`engineering/python-gate-developer.md`](engineering/python-gate-developer.md) |
| Choosing a physics list, cuts, or judging a result | [`engineering/geant4-physics-expert.md`](engineering/geant4-physics-expert.md) |
| Configuring the physics manager, sources, or actors | [`engineering/gate-physics-expert.md`](engineering/gate-physics-expert.md) |
| Configuring or debugging Geant4-DNA **chemistry** (lists, world, scavengers, chemistry actors) | [`engineering/gate-chemistry-expert.md`](engineering/gate-chemistry-expert.md) |
| Adding/moving volumes, solids, materials, fields | [`engineering/gate-geometry-expert.md`](engineering/gate-geometry-expert.md) |
| G4-level geometry, overlaps, navigation, new bindings | [`engineering/geant4-geometry-expert.md`](engineering/geant4-geometry-expert.md) |
| Not sure which engineering role fits | [`engineering/SKILL.md`](engineering/SKILL.md) |
| A simulation crashes, hangs, or gives implausible output | [`engineering/simulation-debugger.md`](engineering/simulation-debugger.md) |
| Adding a test | [`engineering/test-writer.md`](engineering/test-writer.md) |
| Planning work, logging a bug, checking project state | [`status/`](status/task-list.md) |

### Easily-confused pairs — one owner per fact

These skills look overlapping from their titles but own different questions. When in doubt,
read the **owner** column, and follow its links rather than duplicating the content.

| Question | Owner | Not the owner |
| --- | --- | --- |
| "My local setup is broken / how do I make the suite run?" | [`environment-setup`](environment-setup/SKILL.md) §0–§5, §7–§9 | — |
| "How do I ship this / why does CI build wheels?" | [`environment-setup/build-and-ci.md`](environment-setup/build-and-ci.md) | — |
| "How must the code *look* (format, naming, imports)?" | [`code-style`](code-style/SKILL.md) | `architecture`, `python-gate-developer` |
| "How must the code *behave* (lifecycle, `__initcpp__`, managers vs engines)?" | [`architecture`](architecture/SKILL.md) | `code-style` |

Boundary rules the skills themselves enforce:

- **Environment and build/CI/release are one skill family** (`environment-setup/`): `SKILL.md`
  §0–§3/§5/§7–§9 set up your machine, and the two deep-dives own the heavy topics —
  [`geant4-itk.md`](environment-setup/geant4-itk.md) for compiling the native deps and the C++
  extension, [`build-and-ci.md`](environment-setup/build-and-ci.md) for packaging, releasing and CI.
  The former standalone `build-and-ci` skill was merged into `environment-setup` §6 and then
  extracted back into its own file to keep `SKILL.md` an index.
- The **C++/Geant4 build procedure** lives in [`geant4-itk.md`](environment-setup/geant4-itk.md);
  [`build-and-ci.md`](environment-setup/build-and-ci.md) §6 keeps only the packaging consequences.
- The **object-lifecycle rules** are owned by `architecture` §3/§7; the role skills restate
  them for self-containment and link back for the rationale.

## The engineering roles

Eight role-oriented skills layer *on top of* the task-oriented ones above. They answer "how
should I think about this?" rather than "what command do I run?". **Start with
[`engineering/SKILL.md`](engineering/SKILL.md)** — it maps them, explains the two layered pairs,
and says which role to pick.

| Role | Owns | Does **not** cover |
| --- | --- | --- |
| [`python-gate-developer.md`](engineering/python-gate-developer.md) | Python API design, managers/actors/sources, the C++ boundary, serialisation | physics validity, test design |
| [`geant4-physics-expert.md`](engineering/geant4-physics-expert.md) | Geant4 physics lists, EM models, cuts, statistics, physical plausibility | the GATE configuration layer, code structure |
| [`gate-physics-expert.md`](engineering/gate-physics-expert.md) | The GATE physics layer: physics manager, **sources**, **actors**, filters, biasing, normalisation | raw Geant4 model internals |
| [`gate-chemistry-expert.md`](engineering/gate-chemistry-expert.md) | The GATE chemistry layer: chemistry manager/list/world, track-structure EM regions, chemistry actors and counters | the general physics/source/actor machinery, raw Geant4-DNA model internals |
| [`geant4-geometry-expert.md`](engineering/geant4-geometry-expert.md) | Raw G4 geometry: solids, logical/physical volumes, materials, navigation, overlaps, C++ bindings | the GATE user-facing volume API |
| [`gate-geometry-expert.md`](engineering/gate-geometry-expert.md) | The GATE geometry layer: volume tree, solids, materials, placement/repetition, regions, fields | raw G4 navigation internals |
| [`simulation-debugger.md`](engineering/simulation-debugger.md) | Triage, reproduction, lifecycle-localised diagnosis | writing the fix's tests |
| [`test-writer.md`](engineering/test-writer.md) | Test placement, assertions, tolerances, demonstrating failure | the code under test |

The two physics skills and the two geometry skills are **layered, not duplicated**:
`geant4-*-expert` covers the Geant4 model beneath GATE; `gate-*-expert` covers the GATE API
built on top of it (including actors and sources for physics). A change is *designed* with the
matching expert skill, *implemented* with the developer skill, *proved* with the test-writer
skill, and *triaged* with the debugger skill when it goes wrong.

## Conventions every skill follows

1. **Machine-agnostic paths.** No skill hard-codes an absolute path. Per-machine values come
   from `user_secrets.json` at the repo root (git-ignored):
   `OPEN_GATE_REPO`, `OPEN_GATE_ENV`, `OPEN_GATE_DEPS`.
   See [`environment-setup/SKILL.md`](environment-setup/SKILL.md) §0.
2. **Classify before you diagnose.** Every failure is either a *repository bug* or an
   *environment issue*. Most confusing ones are the latter. The distinction is enforced in
   [`status/found-bugs.md`](status/found-bugs.md).
3. **Evidence over claims.** A command that was actually run, with its output — not "should
   work". Test results come from `opengate_tests`, never from an absence of output.
4. **Checklists at the end.** Each skill ends with a "definition of done" / checklist; use it
   before reporting completion.
5. **Skills can be wrong.** They describe the tree at the commit where they were written. If a
   command in a skill fails, fix the skill in the same change
   (`AGENTS.md` §5, hierarchy of truth).

## Status files are part of the workflow

- [`status/task-list.md`](status/task-list.md) — update the same turn you start or finish work.
- [`status/found-bugs.md`](status/found-bugs.md) — log anything you find but do not fix, with
  the **category** filled in.
- [`status/project-status.md`](status/project-status.md) — a *dated* snapshot; correct it when
  it drifts rather than letting it rot.

## Adding a new skill
1. Put task skills in `skills/<topic>/SKILL.md`; put role skills in `skills/engineering/`.
2. **`SKILL.md` is an index, not a textbook.** It states the goal, the scope, the map of where
   things live, and the checklists — then hands off. Anything that needs real depth goes into a
   dedicated `<topic>.md` next to it (the model is [`engineering/`](engineering/SKILL.md): a short
   `SKILL.md` plus one file per role, and
   [`environment-setup/`](environment-setup/SKILL.md): an index plus `geant4-itk.md` and
   `build-and-ci.md`). If your `SKILL.md` passes ~250 lines, split it and repoint the refs — a
   single 800-line file is read in full or not at all.
3. Follow the conventions above (no absolute paths, checklist at the end, cite real evidence).
3. **Add it to the tables in this README and to the skills index in
   [`../AGENTS.md`](../AGENTS.md)** — an undocumented skill is invisible.
4. Keep it self-contained: another agent may read it in isolation.
5. **Check the file is actually trackable** — a skill directory whose name begins with
   `build` is silently ignored by `.gitignore`'s `build*/` rule (B-011). Verify with
   `git check-ignore -v skills/<topic>/SKILL.md` (no output = fine) and confirm it appears in
   `git status`. A skill that cannot be committed does not exist for anyone else.