# Skill: `engineering/simulation-debugger`

**Role:** diagnose why a GATE 10 simulation crashes, hangs, produces nothing, or produces
implausible output — and report the *cause*, not the first symptom.

**The single most important habit here: classify the failure before you investigate it.**
Most confusing failures in this repo are environment problems, not code bugs. Chasing them as
bugs wastes hours and can produce a wrong "fix".

---

## 1. Triage: environment or code? (do this first, it is usually the answer)

| Evidence | Verdict | Action |
| --- | --- | --- |
| `AttributeError: module 'opengate_core' has no attribute 'Gate…'` | stale compiled `opengate_core` | [geant4-itk](../environment-setup/geant4-itk.md) §7 |
| `Geant4 version is not ok` | wrong Geant4 | [environment-setup](../environment-setup/SKILL.md) §3.3 |
| Everything fails with `ModuleNotFoundError: 'opengate'` | venv not activated | [environment-setup](../environment-setup/SKILL.md) §3.1 |
| `Error while reading the file 'output_ref/…'` | test-data submodule behind the recorded commit | [environment-setup](../environment-setup/SKILL.md) §2.1 |
| `cannot allocate memory in static TLS block` | Geant4 TLS model | [geant4-itk](../environment-setup/geant4-itk.md) §6 |
| Import error for `torch`/`gaga_phsp`/`pytomography` | optional extras absent | [environment-setup](../environment-setup/SKILL.md) §5 |
| Reproducible from a clean env, on the pinned Geant4 | **code bug** | continue below |

Run the §7 checklist of `environment-setup` and record the result. Only then treat it as a
repository bug — and say so explicitly in your report.

## 2. Reproduce minimally and deterministically

A bug you cannot reproduce on demand is not yet diagnosed.

```bash
cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"

# serialize + deterministic + easy to read:
opengate_tests -t <subdir>/testNNN_name.py -p sp -n 1
```

- Always activate first — the runner spawns `python <test>` and an un-activated venv fails
  every test opaquely (B-002).
- Read **`opengate/tests/log/<test name>.log`**: the full traceback, not the screen summary.
- Fix the seed when the failure is stochastic; vary it when the failure is intermittent.
- If the test grows, keep the reproduction in a scratch script outside the repo.

## 3. Locate the failure in the simulation lifecycle

GATE 10 runs in ordered phases; the phase tells you where to look.

| Symptom | Likely phase | Look at |
| --- | --- | --- |
| Error while just creating objects (`gate.Simulation()`, `add_actor`) | user phase | the manager's input validation (`opengate/managers.py`) |
| `initialize()` raise | initialization | the object's `initialize()` / `InitializeCpp()` |
| Crash after "Starting simulation" | Geant4 run | geometry overlaps, physics list, C++ side |
| Runs, but the output is empty/zero | scoring | actor `output` config, filters, the scorer's volume |
| Hangs forever | `mp` deadlock / geometry | re-run `-p sp -n 1`; then look for geometry overlaps |
| Nondeterministic crashes under load | resource contention | `-n 4`, often a test/host issue, not code |

## 4. Get more information

- **Verbosity**: raise `sim.verbose_level` (user phase) and
  `g4_verbose_level` / `g4_verbose_level_tracking` (Geant4 / tracking) — see the `user_info`
  block in `opengate/managers.py`.
- **Multiprocessing**: re-run with `-p sp -n 1`. If it passes serially, the bug is in
  serialisation or process handling, not physics.
- **Geometry**: overlaps and "daughter outside mother" are a classic source of empty or wrong
  results; enable Geant4 geometry checks and read them, do not silence them.
- **Dump the state**: `sim.to_json_file(...)` / `json` output shows exactly what was passed;
  diff it against what you intended.
- **Narrow the delta**: does it fail on a bare `gate.Simulation()` + your one object? If not,
  bisect by removing objects until it stops failing.

## 5. Common real causes (ranked by how often they bite)

1. **Stale `opengate_core`** after pulling C++ changes (B-001) — looks like a code bug.
2. **Stale test-data submodule** (B-008/B-009) — looks like a physics/comparison failure.
3. **Your own reproduction harness**, not the repo (see §5.1) — the most under-diagnosed cause.
4. **Wrong physics list for the particles/energies** — see
   [`geant4-physics-expert.md`](geant4-physics-expert.md).
5. **Wrong units.** GATE 10 accepts units as strings; a silently wrong unit scale produces
   plausible, systematically wrong output.
6. **A `g4_` object not created**, or an `initialize()` that skipped `InitializeCpp`.
7. **Geometry overlap / missing mother volume.**
8. **Statistics too low**, or a tolerance that can never be met (see
   [`test-writer.md`](test-writer.md)).
9. **Resource contention** when the full suite runs in parallel.

### 5.1 “My harness is broken” — the third category, and the one that fools you
When you write a scratch script to reproduce an upstream issue, the failure modes of **the script**
look exactly like the bug you are hunting: zero counts, a crash, an “overlap”, a list that “does not
work”. Before you log anything as a repository bug, prove the harness is sound.

Every item below was actually hit in this repository while triaging upstream issues — none of them
crashes in an obvious way.

| What you see | What it really is | Fix |
| --- | --- | --- |
| `Exception: Cannot use both the two parameters 'number_of_primaries' and 'activity'` raised *in a child process*, so the parent only shows `The queue is empty. The spawned process probably died or crashed.` | **Two harness errors stacked**: an invalid source config, then a misleading parent-level message. | Set exactly one of the two. Read the **child** traceback (the parent's message is a symptom, not the cause). |
| `RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase.` | `sim.run(start_new_process=True)` without a `if __name__ == "__main__":` guard, on a **spawn** platform (macOS/Windows). | Wrap the entry point in `if __name__ == "__main__":`. |
| `G4Exception : Run0254 … G4VUserPhysicsList::SetParticleCuts : No Default Region … Aborting` | Instantiating a physics list **outside** a simulation (`create_reference_physics_list_class("X")(0)`). | Only instantiate inside a run; to check a name, run a minimal simulation. |
| `Overlap is detected … fully encapsulating volume …` then `Fatal: Some volumes overlap` | Boolean **operands were also placed** as normal volumes. | `operand.build_physical_volume = False` on both operands — see [`gate-geometry-expert.md`](gate-geometry-expert.md) §4.1. |
| `⚠️ Empty output, no particles stored in …phsp.root` | The scorer was never crossed (too thin, wrong place) or the source never pointed at it. | Sanity-check: does the same beam give ~100 % through an **empty** world? |
| A physics list “not working” | The harness set a **deprecated** parameter (`src.n`) or the wrong beam type. | Check the deprecation message; use `number_of_primaries`. |

**The discipline that catches all of the above — validate against a known answer first:**

1. Build the *simplest* version whose result you can predict (air world, no absorber).
2. Assert it gives that predicted answer (e.g. ~100 % transmission).
3. Only then add the feature under test (the hole, the phantom, the second thread).

A harness that transmits 0 % through air cannot measure a 25 % difference. If you skip step 2, you
will spend the session measuring your own bug — and you may write it into `found-bugs.md` as a
repository defect. **Never log an upstream issue as “confirmed” from a harness that has not been
validated.**

### 5.2 Read the issue's comments before you reproduce anything
Maintainers often post the root cause and the fixing commit in the thread. Re-deriving it is a
wasted session — and, worse, re-running it in the *wrong tree* produces a confidently wrong answer.

**Before reproducing an upstream claim, check the comments for:**

1. **A root-cause explanation** — if it exists, verify the claim in the code instead of re-running
   a long simulation. (Both #1135 and #1143 were fully diagnosed by maintainers; the actionable
   work was to confirm the mechanism and locate the commit, not to reproduce the symptom.)
2. **A fixing commit** — then run `git merge-base --is-ancestor <commit> HEAD` to see whether your
   tree already contains it.
3. **`git tag --contains <fixing-commit>`** — **this is the one people skip.**

**A claim about a *released* version cannot be tested on a tree that is ahead of that release.**
Real example from this repository: #1135 (“TLEDoseActor spikes under 8 threads”) was fixed on
`master` by `a92a62bf1`, but `git tag --contains a92a62bf1` returns **nothing** — the newest release
`10.1.1` does not contain it. So:

- a user on the released wheel **still sees the bug** — their report is valid;
- running it in a `master` checkout looks **clean**, and concluding “not reproduced” would be
  **wrong** — you would have dismissed a real defect.

This is the mirror image of §5.1: there, the harness faked a bug; here, the *tree* hides one. In
both cases the fix is to check what you are actually measuring before you report a verdict.

## 6. Reporting a failure you cannot fix

Log it in [`../status/found-bugs.md`](../status/found-bugs.md) using the template, with the
**category** field filled in (`environment issue` vs `repository bug`). A report without:

- exact commands,
- environment (commit, OS, Python, Geant4),
- the first error line,

is not actionable. If it *is* an environment issue, fix the environment instead of the repo.

## 7. Definition of done
- [ ] Failure classified: environment issue, repository bug, **or harness error** — stated explicitly.
- [ ] Minimal, deterministic reproduction (seed + exact command).
- [ ] The reproduction was validated against a case whose answer was known in advance (§5.1).
- [ ] Child-process tracebacks read, not just the parent's `queue is empty` symptom.
- [ ] Root cause identified, not just the first symptom.
- [ ] The cause is fixed where it actually belongs (environment, harness, or a code commit).
- [ ] The relevant test passes after the fix, and you ran it yourself.
- [ ] Findings recorded in `../status/found-bugs.md` if not fixed immediately.
