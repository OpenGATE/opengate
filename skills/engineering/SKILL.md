# Skill: engineering

**Goal:** pick the right *engineering role* for the work in front of you, then read that role's
playbook.

The files in this directory are **role skills**: they answer "how should I think about this?"
rather than "what command do I run?". The task-oriented skills live one level up:
[`../environment-setup/SKILL.md`](../environment-setup/SKILL.md) (env **and** build/CI/release,
§6),
[`../running-tests/SKILL.md`](../running-tests/SKILL.md),
[`../code-style/SKILL.md`](../code-style/SKILL.md),
[`../architecture/SKILL.md`](../architecture/SKILL.md),
[`../documentation/SKILL.md`](../documentation/SKILL.md). They are referenced *from* the role
skills, not duplicated by them.

Start from [`../../AGENTS.md`](../../AGENTS.md) if you are new to the repository. The map of the
whole `skills/` tree is in [`../README.md`](../README.md).

---

## 1. The roles in this directory

| Role skill | Use it when | Owns | Does **not** cover |
| --- | --- | --- | --- |
| [`python-gate-developer.md`](python-gate-developer.md) | You write or refactor `opengate/**` Python code | Python API design, managers/actors/sources, the C++ boundary, serialisation | physics validity, test design |
| [`geant4-physics-expert.md`](geant4-physics-expert.md) | You choose a physics list / cut, or judge whether a result is physically plausible | Geant4 physics lists, EM models, cuts, statistics, realism | the GATE configuration layer, code structure |
| [`gate-physics-expert.md`](gate-physics-expert.md) | You configure the physics manager, **sources**, or **actors** | The GATE physics layer: physics manager, sources, actors, filters, biasing, normalisation | raw Geant4 model internals |
| [`geant4-geometry-expert.md`](geant4-geometry-expert.md) | You work at the raw G4 geometry layer, or add a geometry binding | G4 solids, logical/physical volumes, materials, navigation, overlaps, C++ bindings | the GATE user-facing volume API |
| [`gate-geometry-expert.md`](gate-geometry-expert.md) | You add or move volumes, solids, materials, regions or fields | The GATE geometry layer: volume tree, solids, materials, placement/repetition, regions | raw G4 navigation internals |
| [`simulation-debugger.md`](simulation-debugger.md) | A simulation crashes, hangs, or gives implausible output | Triage, reproduction, lifecycle-localised diagnosis | writing the fix's tests |
| [`test-writer.md`](test-writer.md) | You add or refactor a test | Test placement, assertions, tolerances, demonstrating failure | the code under test |

## 2. The two layered pairs — do not read both by default

The physics and geometry roles each come as a **pair**, deliberately split by **layer** so you
read one, not two:

| Layer | Physics | Geometry |
| --- | --- | --- |
| **Geant4** (the model beneath GATE) | [`geant4-physics-expert.md`](geant4-physics-expert.md) | [`geant4-geometry-expert.md`](geant4-geometry-expert.md) |
| **GATE** (the API built on it) | [`gate-physics-expert.md`](gate-physics-expert.md) | [`gate-geometry-expert.md`](gate-geometry-expert.md) |

- The **`geant4-*`** skills explain *why* the underlying engine behaves as it does — patch-level
  physics, G4 object model, navigation, overlaps, the C++ layer in `core/`.
- The **`gate-*`** skills explain *how you configure and exploit it* — the managers, the volume
  tree, **sources** and **actors**, regions, normalisation, filters.

Each file states in its opening section when you are in *that* skill and not its sibling. When a
change spans both layers (a geometry change with a physics consequence, or a new binding), read
both — the GATE skill first, then the Geant4 one for the mechanism.

## 3. How the roles compose

A change is *designed* with the matching expert skill, *implemented* with the developer skill,
*proved* with the test-writer skill, and *triaged* with the debugger skill when it goes wrong.

```
design (physics / geometry expert)  →  implement (python-gate-developer)
      →  prove (test-writer)        →  triage (simulation-debugger) when it fails
```

Worked examples:

| Task | Roles, in order |
| --- | --- |
| Add a new dose scorer | `gate-physics-expert` (what to score, normalisation) → `python-gate-developer` (the class) → `test-writer` |
| Move a detector / add a phantom | `gate-geometry-expert` (tree, materials) → `geant4-geometry-expert` if an overlap or binding is involved → `test-writer` |
| Change the physics list for a hadron therapy study | `geant4-physics-expert` (list choice, cuts) → `gate-physics-expert` (how to set it) → `test-writer` |
| A simulation gives plausible-but-wrong numbers | `simulation-debugger` (classify) → the matching expert skill (is it physics or geometry?) |

## 4. Conventions every role skill follows

1. **Environment first.** Each role opens by telling you to prove the environment is correct
   (Geant4 version OK, no stale-`.so` warning) before drawing any conclusion. A physics or
   geometry conclusion on a wrong build is worthless — see
   [`../environment-setup/SKILL.md`](../environment-setup/SKILL.md).
2. **Machine-agnostic paths.** No role skill hard-codes an absolute path; per-machine values come
   from `user_secrets.json` (`OPEN_GATE_REPO`, `OPEN_GATE_ENV`, `OPEN_GATE_DEPS`).
3. **Classify before you diagnose.** Every failure is a *repository bug* or an *environment issue*
   ([`../status/found-bugs.md`](../status/found-bugs.md)).
4. **Evidence over claims.** A command actually run, with its output — not "should work".
5. **Cite real names.** The role skills name real classes and parameters
   (`SolidBase`, `GenericSource`, `DoseActor`, `reference_physics_list_*`, …) taken from the
   code; never invent a Geant4 class name — grep `core/` for the wrapper first.
6. **A checklist at the end.** Each role skill ends with a "definition of done"; use it before
   reporting completion.

## 5. Adding a role skill

1. Create `skills/engineering/<role-name>.md`, opening with `# Skill: engineering/<role-name>`
   and a one-paragraph `**Role:**` statement.
2. Say explicitly what the role **does not** cover, and link the neighbouring role it is often
   confused with (the two layered pairs above are the model).
3. Follow the conventions in §4 — no absolute paths, cite real code names, checklist at the end.
4. **Add it to the tables in this file, in [`../README.md`](../README.md) and in the skills index
   of [`../../AGENTS.md`](../../AGENTS.md)** — an undocumented skill is invisible.

## 6. Checklist

- [ ] You picked the role matching your task (§1), or the correct layer of a pair (§2).
- [ ] You read the role's **environment-first** section and confirmed the build is correct.
- [ ] The role's "Does not cover" column sent you to the right sibling skill if needed.
- [ ] You used the role's definition-of-done checklist before reporting completion.
- [ ] If a command in a role skill was wrong, you fixed the skill in the same change
      (`../../AGENTS.md` §5).
