# Skill: running-tests

**Goal:** run the right tests, fast, and report results with real evidence.

GATE 10 has its own test runner (`opengate_tests`). It is **not** pytest. Each test is a
standalone `testXXX_*.py` script that returns/prints a status; the runner executes them,
collects results and writes a JSON dashboard.

---

## 1. Entry point and where tests live

```bash
opengate_tests [OPTIONS]      # console script -> opengate/bin/opengate_tests.py
```

Tests: `opengate/tests/src/`, split into sub-directories:

```
actors/ advanced_tests/ chemistry/ external/ geometry/ misc/ physics/ source/
```

Helpers: `opengate/tests/utility.py` (`test_ok`, `assert_images_equal`, …).
Runner internals: `opengate/bin/opengate_tests_helpers.py`.

## 2. Options you will actually use

From `opengate/bin/opengate_tests.py`:

| Option | Meaning |
| --- | --- |
| `--start_id/-i`, `--end_id/-e` | Numeric range of tests to run (`default="all"`). |
| `--test/-t PATH` | Run one explicit test, path relative to `opengate/tests/src`. **Repeatable.** |
| `--random_tests/-r` + `--seed/-s` | Run the last 10 tests + 1/4 of the others randomly. This is what CI uses. |
| `--processes_run/-p` | `'mp'` (default, multiprocessing), `'sp'`, `'legacy'`. |
| `--num_processes/-n` | Number of processes, default `all` cores. |
| `--run_previously_failed_jobs/-f` | Re-run only tests that failed in the previous dashboard. |
| `--no_log_on_fail` | Do not dump the log of failing tests to stdout. |
| `--print_last_test/-l` | Print the highest `testNNN` number and exit (useful for adding a new test). |
| `--g4_version/-v` | Developer override for the Geant4 version string check, e.g. `-v v11.4.2`. |

Examples:

```bash
opengate_tests -t source/test008_dose_actor.py           # one test
opengate_tests -t source/test008_dose_actor.py -t actors/test019_dose_actor_simple.py
opengate_tests -i 15 -e 20                               # numeric slice
opengate_tests -f                                        # only last-run failures
opengate_tests -p sp -n 1                                # serial, deterministic, easy to debug
opengate_tests -l                                        # highest test id
```

**Never** run the whole suite as a first move: it is long, needs many cores, downloads
Geant4 + test data on first run, and the output is unreadable. Slice it.

## 3. Running a single test standalone

For interactive debugging, a test can be executed directly:

```bash
python opengate/tests/src/source/test008_dose_actor.py
```

The script prints `OK`/error lines and may write into `opengate/tests/output/`. This is
fine for debugging a single case, but **report suite results only from `opengate_tests`**,
which is what CI runs and what the dashboard tracks.

## 4. Interpreting results

- The runner prints a summary; interleaved per-test logs appear on failure unless
  `--no_log_on_fail` is set.
- The JSON dashboard is written to `opengate/tests/output_dashboard/dashboard_output*.json`.
  Keys are test paths, values are `[status, ...]` — an empty/`""` status means "not run
  yet", which is exactly what `-f` reads to re-run failures.
- History of CI runs: <https://opengate.github.io/opengate_tests_results>
- A test returning non-`True` from its final check = failure. Read the log; do not guess.

## 5. Writing a new test

1. Find the current highest id: `opengate_tests -l`.
2. Create `opengate/tests/src/<subdir>/testNNN_short_name.py` (next free number, zero
   padded, snake_case topic).
3. Import helpers: `from opengate.tests import utility`.
4. Structure:
   - create the simulation with the public API (`gate.Simulation`, `gate.add_*`);
   - run it;
   - assert on real output (dose, phase space, produced particles, geometry params)
     using `utility` helpers;
   - end with a `utility.test_ok(condition)` style check so the runner sees a verdict.
5. Tests must be self-contained, use only `opengate/tests/data` (or generated data) as
   input, and write to `opengate/tests/output/` only.
6. Keep runtimes small (seconds to a couple of minutes); CI runs the whole matrix.
7. If you add an example that is also user documentation, mirror it under `docs/` (see
   `skills/documentation`).

## 6. Keeping tests honest

- Vary the seed / statistics when a test asserts on stochastic quantities; a test that
  passes only with one seed is a bug in the test.
- Prefer asserting on *physics-relevant* quantities with justified tolerances over
  exact float equality on simulation output.
- If the test needs torch/gaga-phsp/pytomography, note it in the docstring — CI installs
  those, a bare dev env may not.

## 7. Checklist before reporting a test result

- [ ] Environment verified per `skills/environment-setup/SKILL.md`.
- [ ] Exact command line quoted in the report.
- [ ] Pass/fail taken from the dashboard or the summary, not from absence of output.
- [ ] For failures: the top of the traceback + the test's own assertion line included.
- [ ] Nothing generated was left in the git index (`git status` clean of outputs).