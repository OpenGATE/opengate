# Skill: running-tests

**Goal:** run the right tests, fast, and report results with real evidence.

GATE 10 has its own test runner (`opengate_tests`). It is **not** pytest. Each test is a
standalone `testXXX_*.py` script that returns/prints a status; the runner executes them,
collects results and writes a JSON dashboard.

**Two prerequisites, both verified as easy to get wrong** (details in
`skills/environment-setup`):

1. **The environment must be the one the user designated** — `OPEN_GATE_ENV` from
   `user_secrets.json` (root of the repo, git-ignored; see `skills/environment-setup` §0),
   a non-volatile path — and it must be **activated**, not merely referenced by absolute
   path. The runner shells out to the literal command `python <test>`; an un-activated venv
   makes every single test fail with `ModuleNotFoundError: No module named 'opengate'`.
2. **The environment must be consistent** — a stale compiled `opengate_core` fails at
   import before the runner even starts (`skills/environment-setup` §4.6).

---

## 1. Entry point and where tests live

```bash
cd "$OPEN_GATE_REPO"                     # user's path, from user_secrets.json
export OPEN_GATE_ENV="$(python3 -c 'import json;print(json.load(open("user_secrets.json"))["OPEN_GATE_ENV"])')"
source "$OPEN_GATE_ENV/bin/activate"     # MUST activate — see environment-setup §3.1
opengate_tests [OPTIONS]                 # console script -> opengate/bin/opengate_tests.py
```

Tests: `$OPEN_GATE_REPO/opengate/tests/src/`, split into sub-directories (458 test files
in this tree: 368 to run, 90 ignored):

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

Examples (verified against this tree — see the `-t` path warning below):

```bash
opengate_tests -t actors/test008_dose_actor.py           # one test
opengate_tests -t actors/test008_dose_actor.py -t misc/test011_mt.py
opengate_tests -i 1 -e 12 -n 4                           # numeric slice, 4 processes
opengate_tests -f                                        # only last-run failures
opengate_tests -p sp -n 1                                # serial, deterministic, easy to debug
opengate_tests -l                                        # highest test id (114 here)
```

**`-t` paths are relative to `opengate/tests/src` and must include the subdirectory**
(`actors/…`, `source/…`, `misc/…`). A path outside that folder aborts the whole run with
`Exception: Explicit test paths must point inside the OpenGATE tests/src folder`, and a
path that does not exist there aborts with `…were not found among available tests`. There
is no `source/test008_dose_actor.py` — `test008_dose_actor.py` lives in `actors/`. Find
the real path first:

```bash
find "$OPEN_GATE_REPO/opengate/tests/src" -name 'test008*.py'
```

**Activate the environment before running** — the runner spawns each test as the literal
shell command `python <test path>` (`opengate/bin/opengate_tests_helpers.py`), so an
un-activated venv makes every test fail with `ModuleNotFoundError: No module named
'opengate'`. See `skills/environment-setup` §3.1.

**Never** run the whole suite as a first move: it is long (458 test files here; 368 to
run, 90 ignored), needs many cores, downloads Geant4 + test data on first run, and the
output is unreadable. Slice it.

## 3. Running a single test standalone

For interactive debugging, a test can be executed directly (from `$OPEN_GATE_REPO`, with
the environment activated):

```bash
source "$OPEN_GATE_ENV/bin/activate"
cd "$OPEN_GATE_REPO"
python opengate/tests/src/actors/test008_dose_actor.py
```

The script prints `OK`/error lines and may write into `opengate/tests/output/`. This is
fine for debugging a single case, but **report suite results only from `opengate_tests`**,
which is what CI runs and what the dashboard tracks.

When invoked through the runner, each test's output is also captured to
`opengate/tests/log/<test name>.log` (e.g. `opengate/tests/log/test008_dose_actor.log`),
which is the fastest place to read a failure.

## 4. Interpreting results

- The runner prints a summary; interleaved per-test logs appear on failure unless
  `--no_log_on_fail` is set.
- Each test's full output is also written to `opengate/tests/log/<test name>.log` — the
  fastest place to read a failure when the screen output is long.
- **Before believing a failure, rule out the environment**: a stale `opengate/tests/data`
  submodule, a wrong Geant4 version, or a stale `opengate_core` all produce failures that
  look like code bugs (see `skills/environment-setup` §2.1, §3.3, §4.6). A reference-data
  failure reads like `Error while reading the file 'output_ref/…'` — check the submodule
  commit before anything else.
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