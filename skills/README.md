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
├── environment-setup/SKILL.md     get a working dev env where ALL tests run
├── running-tests/SKILL.md         the opengate_tests runner, filters, dashboard
├── build-and-ci/SKILL.md          wheels, CI topology, version bump
├── code-style/SKILL.md            pre-commit / black / clang-format, conventions
├── architecture/SKILL.md          managers / engines / actors / sources lifecycle
├── documentation/SKILL.md         Sphinx pages and local build
├── engineering/
│   ├── python-gate-developer.md   write Python API code that fits the design
│   ├── geant4-physics-expert.md   physics lists, cuts, statistics, realism
│   ├── simulation-debugger.md     diagnose crashes / hangs / implausible output
│   └── test-writer.md             write tests that actually catch regressions
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
| Touching `core/`, wheels, `pyproject.toml`, or `.github/workflows/` | [`build-and-ci/SKILL.md`](build-and-ci/SKILL.md) |
| About to commit | [`code-style/SKILL.md`](code-style/SKILL.md) |
| Adding an actor / source / engine / manager | [`architecture/SKILL.md`](architecture/SKILL.md) |
| Adding or changing a docs page | [`documentation/SKILL.md`](documentation/SKILL.md) |
| Writing or refactoring `opengate/**` Python code | [`engineering/python-gate-developer.md`](engineering/python-gate-developer.md) |
| Choosing a physics list, cuts, or judging a result | [`engineering/geant4-physics-expert.md`](engineering/geant4-physics-expert.md) |
| A simulation crashes, hangs, or gives implausible output | [`engineering/simulation-debugger.md`](engineering/simulation-debugger.md) |
| Adding a test | [`engineering/test-writer.md`](engineering/test-writer.md) |
| Planning work, logging a bug, checking project state | [`status/`](status/task-list.md) |

## The engineering roles

Four role-oriented skills layer *on top of* the task-oriented ones above. They answer "how
should I think about this?" rather than "what command do I run?".

| Role | Owns | Does **not** cover |
| --- | --- | --- |
| [`python-gate-developer.md`](engineering/python-gate-developer.md) | Python API design, managers/actors/sources, the C++ boundary, serialisation | physics validity, test design |
| [`geant4-physics-expert.md`](engineering/geant4-physics-expert.md) | Physics lists, cuts, EM models, statistics, physical plausibility | code structure, build issues |
| [`simulation-debugger.md`](engineering/simulation-debugger.md) | Triage, reproduction, lifecycle-localised diagnosis | writing the fix's tests |
| [`test-writer.md`](engineering/test-writer.md) | Test placement, assertions, tolerances, demonstrating failure | the code under test |

They are deliberately complementary: a physics change is *designed* with the physics skill,
*implemented* with the developer skill, *proved* with the test-writer skill, and *triaged* with
the debugger skill when it goes wrong.

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
2. Follow the conventions above (no absolute paths, checklist at the end, cite real evidence).
3. **Add it to the tables in this README and to the skills index in
   [`../AGENTS.md`](../AGENTS.md)** — an undocumented skill is invisible.
4. Keep it self-contained: another agent may read it in isolation.