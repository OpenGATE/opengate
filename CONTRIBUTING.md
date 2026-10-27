# Guidelines for developers

Short rules to keep OpenGATE consistent. For installation and
the code structure, see the
[developer guide](https://opengate-python.readthedocs.io/en/master/developer_guide/index.html).

**TL;DR**

- Contact the maintainers first: another group may already be working on what
  you plan.
- One PR = one feature or bug fix, with its test and its documentation.
- AI-assisted code is welcome, but YOU are responsible for making it work
  properly.
- Have fun!

## Branches and pull requests

- Start a branch from the current `master`, one topic per branch.
- Prefer a small PR, with a clear title and description, over a large one.
  Open it early, as a draft if needed.
- Write `Fixes #NNN` in the description when the PR solves an issue.
- Tick "Allow edits by maintainers".
- Do not commit generated files: test outputs, build folders, `__pycache__`,
  local `simulation.json`, and so on.

## Code

- Format with [pre-commit](https://pre-commit.com/), which runs black for
  Python and clang-format for C++: `pip install pre-commit`, then
  `pre-commit install` in the repository.
- Every user parameter (`user_info_defaults`) has a real `doc` string: no
  `FIXME`, and the units are stated.
- Physical values use Geant4 units (`gate.g4_units`), including times and
  durations.
- For user errors, call `fatal()` with a message that says what to change. Use
  `warning()` only when the simulation can go on. Never use a bare `except:`;
  catch the specific exception and print it.
- A new C++ class exposed to Python needs its `init_...` function, declared
  and called in `core/opengate_core/opengate_core.cpp`.

## Tests

- Every new feature or bug fix comes with a test, which also serves as an
  example for users.
- Name: `opengate/tests/src/<category>/testNNN_short_name.py`. NNN is a new
  number: `opengate_tests -l` prints the last one used on your branch. Also
  check the open PRs, to avoid a clash. Files that share a number belong to
  the same feature.
- The file is executable (`chmod a+x`), starts with `#!/usr/bin/env python3`,
  and ends with `utility.test_ok(is_ok)`.
- Use `utility.get_default_test_paths(__file__, ...)` for the data and output
  folders. Write nothing elsewhere.
- Name suffixes have a meaning for the test runner:
  - `_helpers.py`: shared code, not run as a test;
  - `_wip`: work in progress, not run;
  - `_mt`: multithreaded;
  - `_jobs_`: runs split jobs (scheduled separately).
- Keep tests short, a few tens of seconds at most.
- Large reference data go to the test data repository (submodule
  `opengate/tests/data`, on gitlab.in2p3.fr), not to this repository. Ask a
  maintainer.
- Run your test, and the tests of the parts you changed, before pushing:
  `./testNNN_short_name.py`, or `opengate_tests -t <category>/testNNN_short_name.py`.

## Continuous integration

- A PR that does not touch the C++ (`core/`) reuses the core wheels already
  built on `master`, so only the tests are run. Add the `build-core` label to
  force a full build.
- All tests must pass on all platforms before merging.

## Documentation

- A new or changed feature updates the user guide (`docs/source/user_guide/`),
  and the developer guide (`docs/source/developer_guide/`) when the design
  changes.
