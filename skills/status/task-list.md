# Task list (agent-maintained)

Shared work list for agents and humans on this repository. **Update it in the same turn
you start or finish work** — an agent that plans work here but does not mark it done makes
the next agent repeat it.

Rules:

- One line per task, with a stable id (`T-001`, `T-002`, …).
- Status is one of: `todo`, `doing`, `blocked`, `done`, `dropped`.
- Always name the files/areas touched, so the next reader can find the change.
- When a task reveals a bug you are not fixing now, add it to
  [`found-bugs.md`](found-bugs.md) and link the bug id here.
- Keep `done` tasks for one release cycle, then move them to the archive at the bottom.

Columns: **id · status · area · task · evidence**.

---

## Active

| id | status | area | task | evidence |
| --- | --- | --- | --- | --- |
| T-001 | done | `AGENTS.md`, `skills/` | Add agent entry point + skills for environment setup, tests, build/CI, code style, architecture, docs, and a status folder. | Files added on branch `agentic-skills`; see this directory. |
| T-002 | todo | `skills/` | Keep skills in sync with the code: any PR that changes test runner options, CI keys, or the object lifecycle must update the matching `SKILL.md`. | — |
| T-003 | todo | `skills/environment-setup` | Record the exact commands (and their output) that were verified on each supported OS, so the setup path is reproducible rather than assumed. | — |
| T-004 | todo | ops | Decide how generated session logs (`opengate/tests/log/`, `output_dashboard/`) are shared between agents without being committed. | — |

## Blocked

| id | status | area | task | blocker |
| --- | --- | --- | --- | --- |
| — | — | — | *(none)* | — |

## Archive (completed)

| id | status | area | task | evidence |
| --- | --- | --- | --- | --- |
| — | — | — | *(nothing archived yet)* | — |

---

## How to use this file without creating noise

1. Before starting work: search this file for the area you are touching. If a task
   exists, switch it to `doing` and add your name/agent id.
2. Do not create a task for a one-line fix that you complete immediately — such work is
   visible in git history.
3. `evidence` is mandatory for `done`: the command you ran, the commit hash, or the file
   you changed. "Looks fine" is not evidence.
4. If you drop a task, say **why** in the task line rather than deleting it silently.