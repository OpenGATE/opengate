Developer guide: Progress Hook Architecture
===========================================

Overview
--------

The **Progress Hook** system provides periodic runtime execution monitoring during Geant4 event loops in OpenGATE.

Architecture
------------

The progress hook bridges C++ event generation loops with Python execution contexts:

1. **C++ Side (`GateSourceManager`)**:
   - Holds `fProgressReportCallback` (`py::function`) and `fProgressReportInterval` (in real seconds).
   - In `GateSourceManager::GeneratePrimaries()`, `CheckProgressReport()` is invoked on event generation.
   - Evaluates elapsed real wall-clock time (`std::chrono::steady_clock`).
   - Acquires the Python GIL (`py::gil_scoped_acquire`) before invoking the Python callback safely.
   - In MT mode, `CheckProgressReport()` runs on worker thread managers to deliver periodic updates.

2. **Python Engine (`SourceEngine` in `engines.py`)**:
   - In `SourceEngine.start()`, checks `sim.progress_hook`.
   - Attaches `sim.progress_hook` (and `sim.progress_hook_interval`) to Thread 0's source manager (`g4_thread_source_managers[0]` in MT mode, or `g4_master_source_manager` in ST mode).
   - Upon simulation completion, invokes `sim.progress_hook("completed")`.

3. **User Hooks Module (`userhooks.py`)**:
   - `gate.progress_status(filename, interval)` is a factory function creating a progress status reporter callback.
   - Aggregates total events across `g4_master_source_manager` and all worker managers in `g4_thread_source_managers`.
   - Computes elapsed time, progress ratio, and current simulation time before dumping the JSON payload.
