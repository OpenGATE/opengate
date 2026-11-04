
Please, consider the README.md file in the main opengate folder.

## Last Vertex worker state

`GateLastVertexInteractionSplittingActor` keeps its mutable transport state in
one `G4Cache<WorkerState>` per actor: genealogy, replay containers, track/step
copies, physical process and stack pointers, source identity, acceptance manager,
volume traversal state and counters. Configuration stays shared read-only.
At run start, the actor obtains the current worker's `GateSourceManager` from
its Geant4 primary generator. Sources are already instantiated per worker by
the Python source engine; this change does not create additional sources.

Counters accumulate locally across runs and are reduced once at worker completion.
The reduction uses one lock per worker, with no new locks in transport callbacks.
Worker-owned track/step copies and acceptance objects are released before teardown.
The existing Python counter getters return the reduced totals after transport.

This is the state-localization stage, not complete MT support. The actor remains
declared non-MT-ready. Current-event source provenance, replay draining at run
boundaries, other application actors, global stopping and phase-space allocation
still require their planned changes and transport validation. The performance
criterion remains wall time to comparable uncertainty; no speedup is established.

After building the core, run the native regression from the repository root
with the Python interpreter used for that build:

```bash
python core/tests/run_lastvertex_worker_state.py --output-dir /tmp/lv-state-test
```

The output directory must be new. Pass `--build-dir` for another CMake build.
The runner reuses that build's compiler/linker configuration and links a separate
executable without replacing the core. It tests real cache/callback isolation
on 1/2/4/8 native threads, independent actors, counters across simulated run
boundaries, reduction, reset and acceptance-manager cleanup. It does not run
Geant4 transport or establish MT physics correctness or scaling.

## Replay source identity

The LV actor finds exactly one `GateLastVertexSource` by C++ type in the current
worker's source list at run start, caches its pointer and compares it with the
actual generating-source pointer. It selects replays by pointer, without source
name lookups in event or step callbacks. The Python actor likewise identifies
`LastVertexSource` by type for validation and gathered replay counts. Names are
arbitrary, including `None`; a null pointer identifies synthetic events.

Zero or multiple replay sources are rejected explicitly. Multiple independent
LV actor/source pairings are not supported by this automatic discovery. Existing
macros may retain their source names; no new configuration field is required.
The renamed-source CT_40/split-50 smoke reproduces all six images from the
preceding deferred-completion reference exactly, including existing NaNs.
