
Please, consider the README.md file in the main opengate folder.

## Last Vertex worker state

`GateLastVertexInteractionSplittingActor` keeps its mutable transport state in
one `G4Cache<WorkerState>` per actor: genealogy, replay containers, track/step
copies, physical process and stack pointers, source identity, acceptance manager,
and counters. Configuration stays shared read-only.
At run start, the actor obtains the current worker's `GateSourceManager` from
its Geant4 primary generator. Sources are already instantiated per worker by
the Python source engine; this change does not create additional sources.

Counters accumulate locally across runs and are reduced once at worker completion.
The reduction uses one lock per worker, with no new locks in transport callbacks.
Worker-owned track/step copies and acceptance objects are released before teardown.
The existing Python counter getters return the reduced totals after transport.

The actor now permits MT transport after worker-state, source-provenance,
deferred-completion and kill-actor updates. Controlled patient transport checks
are recorded below. This is not physical or correlated-uncertainty validation.
The performance criterion remains wall time to comparable uncertainty; no useful
speedup is established.

## LV deferred run completion

LV replay mode opts the worker source manager into completion after all native
end-event actors and chemistry callbacks. `PrepareNextSource()` stays in
`GeneratePrimaries()` and is not repeated. Other simulations retain their
existing generation-time completion check. LV reads the actual generating
source pointer; synthetic events preserve pending replay state.

`GateVSource::HasPendingEvents()` defaults to false; LastVertexSource reports
unconsumed replay events. A stop criterion or primary cap with pending replays
raises an explicit incomplete-history error. The code neither silently drops
replays nor ignores the cap to generate an endless sequence of geantinos.
The shared stop flag is atomic and resets at the master run boundary. Run
completion advances the worker once and retains the existing Geant4 barrier.
External aborts, fatal errors and SIGINT do not promise graceful replay drainage.

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

## LV dead-code cleanup

Unused actor state and source-template fields have been removed, together with
an unimplemented solid-angle helper, unused process-filter/tree-print helpers,
and the biased-volume traversal whose stored result had no active consumer.
The live ancestor-volume list and its Python binding remain. Splitting helpers
no longer pass unused step/container/process arguments; old commented code and
unused local computations were removed. Callbacks, exported counters, process
wrappers and replay containers remain in use and are retained.

After this cleanup, the maintained renamed-source CT_40/split-50 smoke reproduces
all six preceding reference images exactly, including existing uncertainty NaNs.
This is a regression check, not physical validation or a speed measurement.

## LV-specific non-interacting particle selection

The former `KillNonInteractingParticleActor` is now named
`KillNonInteractingParticleForLVActor` in Python and
`GateKillNonInteractingParticleForLVActor` in C++. The .h/.cpp/binding files and
actor registry use the same name. The old type name is not an alias.

The historical criterion is retained: record the entrance energy/track identity
only under the original first-step/entry conditions, then kill at an ancestor
exit with exactly equal kinetic energy. Tracks born inside the attached volume
retain their exemption; Rayleigh is not distinguished by an energy change.
This is an LV contribution selector, not a general interaction-history classifier.
A null physical volume at world exit is now handled safely.

Mutable entry/track state and killed counts live in `G4Cache<WorkerState>`.
Configuration is shared read-only. Counts accumulate across runs and are reduced
once per worker in `EndOfSimulationWorkerAction`, without per-step locks. Python
reads the reduced count through `GetNumberOfKilledParticles()` and the read-only
`number_of_killed_particles` property. The Python finalization hook also fills
the actor output's count. The actor is MT-ready; LV transport as a whole remains
subject to its other outstanding validation and source-allocation work.

## LV particle-name kill actor

`GateKillAccordingParticleNameLVActor` replaces
`GateKillAccordingParticleNameActor` (.h/.cpp and Python binding). Its Python
factory name is `KillAccordingParticleNameLVActor`; the old name has no alias.
The optional VRT helpers use the new name and remain disabled in the current
patient transport path.

The original rule is preserved: select the configured particle names and kill
only when the track crosses into an ancestor of the attached volume. The
selection flag and killed count use the existing `G4Cache`; counts accumulate
across runs and are reduced at worker completion. The mutex is taken only for
that final reduction. `StartSimulationAction` resets the final total. Null
post-volumes are safe. Python's final count uses the native reduced getter.

## LV process and replay-queue failures

A missing particle/process manager or unresolved splitting process now raises
an explicit LastVertex error before process use. No interaction is silently
skipped. Lookup checks occur in GetProcessFromProcessName, not every step.
On a real replay, the source checks queue size against its advertised count
and checks the index before indexing. These are two integer comparisons; error
strings are assembled only on the failing branch. A mismatch raises an explicit
error with source name, index, expected count and vector size. Existing exhausted-
queue geantino behavior is unchanged. The checks do not promise zero CPU cost;
no performance measurement was made.

The splitting attempt limit and recursive scheduling are unchanged. Genealogy
lookup now uses a local found flag in the existing first-step search: a missing
track raises an explicit error with track and parent IDs before iterator access.
No extra tree traversal or subsequent-step validation is added.

The CT_40/split-50 smoke retains 12717 events, 33 replays and six exact image
matches to the previous reference, including existing uncertainty NaNs.

## Retry limits and full transport checks

The retry thresholds and scheduling were inspected and left unchanged. A native
controlled-process test confirms successive accepted batches retain the first
300 and clear the stack at batch 301, matching the current strict-greater-than
condition. In the zero-accepted recursive path, the batch cutoff is evaluated
only when recursion returns: a case rejecting 301 times makes 302 calls before
unwinding, with the removal counter incremented at each eligible unwind frame.
With production defaults (batch 500, angular max_rejection 10000), a permanently
rejected direction instead raises the angular error at proposal 10002, after
20 full batches. The separate 10000-iteration secondary-generation guard was
reviewed statically; it was not exercised by that controlled Compton test.



Maintained LINAC/RTPlan/patient LV+TLE transports complete all 123 intervals with
CT_40 on 1/2/4/8 workers and the full 4 mm CT on four workers. Each normal case
uses 12684 originals, split 50, seed 20261103 and unchanged physical settings;
generated/classified replay counts match. Thirty exported images fully read,
finite dose/squared arrays, and exact six-image monothread reference agreement.

An additional 8-worker zero-quota case executes 255 real originals and 729
synthetic geantinos, verified at native source gathering before source teardown.
The launcher's legacy total-minus-replays header reports 984 originals there;
this known metadata limitation is not fixed by the actor MT flag. Normal cases
have no such count discrepancy. Correlated replay uncertainty, physical accuracy,
stop-path completeness and meaningful scaling remain separate validation work.
The small CT_40 smoke is slower in MT (28.7/34.5/39.1/42.9 s wall on 1/2/4/8);
these startup/geometry/output-inclusive times are not an equal-uncertainty benchmark.

## Maintained LV mono/MT regression

```bash
python opengate/tests/src/actors/test094_last_vertex_splitting_rtplan_mt.py
```

This compares LV water dose on one and four threads at four sigma.
Agent-only diagnostic harnesses are not part of the maintained test suite.
