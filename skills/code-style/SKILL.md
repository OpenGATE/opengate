# Skill: code-style

**Goal:** make your change pass `pre-commit` and the reviewers on the first try.

Formatting is **enforced by CI** via pre-commit.ci (see the badge in `README.md`): if you
push unformatted code, the bot will amend your PR with a formatting commit, or CI will
show a diff. Just run the hooks locally.

---

## 1. Setup

```bash
python -m pip install pre-commit
cd <repo root>
pre-commit install          # installs the git hook
pre-commit run --all-files  # format everything now
pre-commit run              # only staged files (also runs on commit)
```

## 2. What the hooks are (`.pre-commit-config.yaml`)

| Hook | Rev | Applies to |
| --- | --- | --- |
| `trailing-whitespace` | v6.0.0 | everything |
| `black` | 26.5.1 | `*.py` |
| `clang-format` | v23.1.1 | `*.cxx`, `*.h`, `*.cpp`, … |

There is **no** import sorter, linter or type checker configured. Do not "helpfully"
reformat unrelated files — a PR should diff only what it changes.

## 3. Python conventions used in this repository

Read `opengate/actors/`, `opengate/managers.py` and `opengate/engines.py` before writing
new code; follow the local idiom rather than inventing one.

- **Naming**: `snake_case` for functions/variables/modules, `CamelCase` for classes.
  Public API objects are created via manager factories (e.g. `sim.add_actor(...)`),
  not by calling constructors directly.
- **Attributes named for Geant4 objects** are prefixed `g4_` (e.g. `g4_region`,
  `g4_volume`) — the convention comes from `DesignGuidelines.md` and is still in use.
- **Imports**: absolute imports of the package (`import opengate as gate`,
  `from opengate.actors import ...`). Inside `opengate/tests/src/` tests, import helpers
  as `from opengate.tests import utility`.
- **Heavy dependencies are lazy**: this repo delays importing matplotlib/pandas/torch
  until needed (`LazyModuleLoader` in `opengate/utility.py`). If you add a heavy import
  on a hot path, check this pattern first.
- **Docstrings**: short, describing the user-visible behaviour of the class/function;
  parameters are described where they are non-obvious. No enforced docstring style.
- **Errors**: raise the project's own exceptions/`fatal` from `opengate/exception.py`
  rather than bare `Exception`, so the message is coloured and consistent.
- **Logging**: use `gate.log` / the project logger and `opengate/logger.py` helpers
  instead of `print` in library code. Tests may print freely.
- **Comments** explain *why*; keep them sparse and in English.

## 4. C++ conventions (`core/`)

- clang-format decides layout — no manual alignment.
- Files: headers `*.h`, sources `*.cxx`/`*.cpp`; Geant4-derived helpers keep the
  `Gate*` naming used throughout `core/opengate_core`.
- Bindings live next to the source they expose; when you add a binding, update the
  corresponding `.cpp` that pybind11 compiles and check that `import opengate_core`
  still exposes the symbol.
- C++17 (`-DCMAKE_CXX_FLAGS=-std=c++17`).

## 5. Documentation formatting

- reStructuredText under `docs/source/**`; Sphinx directives, see
  `skills/documentation/SKILL.md`.
- Markdown only at the repo root (`README.md`, `CHANGELOG.md`, `AGENTS.md`, skills).
- Trailing whitespace is stripped everywhere, including `.rst` — long code blocks with
  significant indentation must use Sphinx literal blocks, not whitespace hacks.

## 6. Before committing

```bash
pre-commit run --files <changed files>     # or: pre-commit run --all-files
git status                                 # no build/output artifacts staged
git diff --stat                            # only intended files touched
```

- [ ] Hooks pass locally.
- [ ] Nothing from `.gitignore`'s "DATA & OUTPUTS" list is staged
      (`*.mhd`, `*.raw`, `*.root`, `*.npz`, `*.csv`, `output/`, `data/`, logs).
- [ ] New files in `skills/` or docs are referenced from the relevant index
      (`AGENTS.md` skills table, `docs/source/*/index.rst`).
- [ ] Commit messages describe the *why*; several small commits beat one huge one
      (`docs/source/developer_guide/developer_guide_contribute.rst`).