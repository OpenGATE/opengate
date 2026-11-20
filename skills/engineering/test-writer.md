# Skill: `engineering/test-writer`

**Role:** write tests for this repository that actually catch regressions — in the repo's own
runner, in the right place, with justified assertions.

GATE 10 uses its own runner, **not pytest**. Read
[`../running-tests/SKILL.md`](../running-tests/SKILL.md) for the mechanics; this skill is about
test *design*.

---

## 1. Placement and numbering

- Location: `$OPEN_GATE_REPO/opengate/tests/src/<subdir>/`, where `<subdir>` is one of
  `actors/ advanced_tests/ chemistry/ external/ geometry/ misc/ physics/ source/`.
- Name: `testNNN_short_topic.py`, next free number in the whole suite:

  ```bash
  cd "$OPEN_GATE_REPO" && source "$OPEN_GATE_ENV/bin/activate"
  opengate_tests -l          # highest test id (114 at the time of writing)
  ```

- Helpers live in `opengate/tests/utility.py` — import as
  `from opengate.tests import utility`. Check what already exists before writing new helpers;
  `utility.test_ok(...)`, image comparison and file checks are already there.
- Reference data goes in the test-data submodule (`opengate/tests/data/`), never in the repo.

## 2. Always demonstrate that the test can fail

A test that cannot fail is worse than no test: it consumes suite time and gives false
confidence. Before committing:

1. Run it with your fix → **pass**.
2. Revert your fix (or temporarily break the assertion) → **fail**.
3. Restore → **pass**.

Record the command you used. If step 2 will not fail, the assertion is not testing what you
think.

## 3. What to assert on

Order of preference:

1. **The user-visible outcome** (dose in a region, produced particles, phase-space content,
   geometry parameters) — this is what a regression would break.
2. **A Geant4-level configured value** (set physics list, applied cut, volume placement) when
   the outcome is too slow or too noisy to score.
3. **Never** on an internal variable or an implementation detail that may legitimately change.

Assertions must survive legitimate refactoring. If your test breaks when someone renames a
private helper, it is over-specified.

## 4. Tolerances — justify them, never tune them

Stochastic assertions are where tests rot.

- Derive the tolerance from the statistics: for `N` histories the relative sigma of a scored
  quantity roughly scales as `1/sqrt(N)`. Choose `N` so the tolerance you need is comfortably
  above the noise floor.
- State the statistics in the test (histories, seed) so the tolerance is reproducible.
- A tolerance loosened "until it passed" is a bug report, not a test. If you had to loosen it,
  say so in the test docstring.
- Deterministic quantities (geometry, parameters, file contents) may use exact equality.

## 5. Template

```python
"""
Short description of the behaviour under test.

Needs: <optional deps, e.g. torch / gaga_phsp>   (remove if none)
Statistics: <histories and seed>                  (if the assertion is stochastic)
"""

import opengate as gate
from opengate.tests import utility


def main():
    sim = gate.Simulation()
    sim.random_seed = <int>            # fixed: make the test reproducible
    # minimal configuration — only what this test is about
    ...

    sim.run()

    # assert on the user-visible outcome, with a justified tolerance
    value = <read the produced result>
    is_ok = abs(value - <expected>) < <tolerance>
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
```

## 6. Constraints the suite imposes

- **Self-contained**: no network, no external data beyond `opengate/tests/data`.
- **Write only under `opengate/tests/output*/`** — these paths are git-ignored. A test writing
  elsewhere pollutes the tree and risks being committed (this already happens once: a full run
  leaves `simulation.json` in the repo root, B-006).
- **Keep runtime small** — seconds to a couple of minutes; the suite already runs 368 tests per
  CI matrix entry.
- **No cross-test dependencies** unless you deliberately use the runner's dependency mechanism;
  the runner splits mutually-dependent tests into a second round, which doubles complexity.
- **Declare optional dependencies** in the docstring; the suite skips such tests when the extra
  is absent (e.g. 11 files are skipped for missing `torch`).

## 7. When you write a *scratch reproduction* (not a test), the same rules apply
Triaging an upstream issue means writing a throwaway script. Treat it with the same suspicion as a
test, because a broken scratch script looks exactly like the bug you are hunting — and it is the
fastest way to log a **false** repository bug.

- **Validate the harness against a known answer before using it.** Transmission through an *empty*
  air world must be ~100 %; if your parallel beam gives 0 %, the bug is in your script. (Real
  example: `direction.type = "beam2d"` with `sigma=[0,0]` is not a parallel beam — it recorded
  1 of 50 000 primaries. `momentum` + `momentum=[0,0,1]` recorded 50 003 of 50 000.)
- **Read the child process's traceback.** With `sim.run(start_new_process=True)` the parent often
  reports only `The queue is empty. The spawned process probably died or crashed.`, while the real
  cause (e.g. an invalid source config) is in the child's traceback.
- **A clean exit is not a result.** `⚠️ Empty output, no particles stored` means zero recorded —
  that is a harness signal, not evidence about the code under test.
- **State the statistics** when you compare two configurations. A ratio computed from single-digit
  counts (e.g. 2 vs 8 events) is noise; say so rather than reporting the ratio.
- Full catalogue of these traps: [`simulation-debugger.md`](simulation-debugger.md) §5.1 and
  [`gate-physics-expert.md`](gate-physics-expert.md) §4.1.

## 8. Verify, and be honest about what you did not verify

```bash
source "$OPEN_GATE_ENV/bin/activate"
cd "$OPEN_GATE_REPO"
opengate_tests -t <subdir>/testNNN_your_test.py     # expect: 1/1 passed
opengate_tests -t <subdir>/testNNN_your_test.py -p mp   # must also work under multiprocessing
```

- Multiprocessing (`-p mp`, the default) exercises serialisation: **always run it**, because a
  test that only passes serially is testing an unrealistic path.
- Read the failure in `opengate/tests/log/<test name>.log`, not the screen summary.
- If the test fails for environment reasons, fix the environment first
  ([`../environment-setup/SKILL.md`](../environment-setup/SKILL.md) §2.1, §3.3,
  [`../environment-setup/geant4-itk.md`](../environment-setup/geant4-itk.md) §7) — do not
  weaken the assertion to accommodate a broken environment.

## 9. Definition of done

- [ ] Correct subdirectory, next free `testNNN_` number, snake_case topic.
- [ ] Demonstrated to fail without the change and pass with it.
- [ ] Asserts on a user-visible outcome; tolerance derived from the statistics and stated.
- [ ] Fixed seed; deterministic given that seed.
- [ ] Writes only to `opengate/tests/output*/`.
- [ ] Passes under `-p mp`.
- [ ] Runtime acceptable; optional deps documented.
- [ ] Any scratch reproduction was validated against a known-case answer before its result was used.
- [ ] The command and result quoted in your report — never "should pass".