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
3. **Wrong physics list for the particles/energies** — see
   [`geant4-physics-expert.md`](geant4-physics-expert.md).
4. **Wrong units.** GATE 10 accepts units as strings; a silently wrong unit scale produces
   plausible, systematically wrong output.
5. **A `g4_` object not created**, or an `initialize()` that skipped `InitializeCpp`.
6. **Geometry overlap / missing mother volume.**
7. **Statistics too low**, or a tolerance that can never be met (see
   [`test-writer.md`](test-writer.md)).
8. **Resource contention** when the full suite runs in parallel.

## 6. Reporting a failure you cannot fix

Log it in [`../status/found-bugs.md`](../status/found-bugs.md) using the template, with the
**category** field filled in (`environment issue` vs `repository bug`). A report without:

- exact commands,
- environment (commit, OS, Python, Geant4),
- the first error line,

is not actionable. If it *is* an environment issue, fix the environment instead of the repo.

## 7. Definition of done

- [ ] Failure classified: environment issue or repository bug — stated explicitly.
- [ ] Minimal, deterministic reproduction (seed + exact command).
- [ ] Root cause identified, not just the first symptom.
- [ ] The cause is fixed where it actually belongs (environment, or a code commit).
- [ ] The relevant test passes after the fix, and you ran it yourself.
- [ ] Findings recorded in `../status/found-bugs.md` if not fixed immediately.