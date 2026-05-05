Initialization sequence for actors
==================================


Here is the chronological initialization sequence for actors, mapping the bridge between Python and C++.

### Monothread (ST) Initialization Sequence

1. **`actor_engine.initialize()` (Python):** Python master loop triggers actor configuration before Geant4 builds the geometry.
2. **`InitializeUserInfo()` & `InitializeCpp()` (C++):** Extracts parameters from the Python dictionary (e.g., splitting factors, kill volumes) and registers the C++ actor instance.
3. **`g4_RunManager.Initialize()` (C++):** Geant4 constructs the master mass and parallel geometries.
4. **`ConstructSDandField()` (Python/C++):** Geant4 triggers OpenGATE to handle sensitive detectors and biasing operators.
5. **`ConfigureForWorker()` (C++):** The actor looks up the main `G4LogicalVolume` and attaches itself (and to all daughter volumes).
6. **`actor_engine.register_actions()` (Python):** Binds the Python actor to the master thread's Tracking, Stepping, Event, and Run action lists.
7. **`StartTracking()` (C++):** Triggered natively by Geant4 when a particle track begins, resetting tracking flags.


### Multithread (MT) Initialization Sequence

1. **`actor_engine.initialize()` (Python):** Executed strictly on the Master Thread to push Python parameters to C++ before workers exist.
2. **`InitializeUserInfo()` & `InitializeCpp()` (C++):** Executes on the Master Thread to save variables (must *not* initialize thread-local pointers here).
3. **`g4_RunManager.InitializeWithoutFakeRun()` (C++):** Geant4 builds the master geometry but holds off on worker creation.
4. **`FakeBeamOn()` (C++):** Geant4 officially spawns the worker threads.
5. **`ConstructSDandField()` (Python/C++):** Triggered by Geant4 independently *for every single worker thread*.
6. **`ConfigureForWorker()` (C++):** Called per worker. The actor securely attaches itself to the thread-local instances of the `G4LogicalVolume`.
7. **`actor_engine.register_actions()` (Python):** Binds the Python actor to the newly created, thread-local Geant4 action lists.
8. **`PreUserTrackingAction()` (C++):** OpenGATE's mandatory MT hook to force tracking initialization (since Geant4 skips native `StartTracking` for MT biasing operators).
9. **`StartTracking()` (C++):** Triggered by `PreUserTrackingAction`. Lazy-initializes the thread-local caches (`threadLocalData.Get()`), instantiates the thread-local operations, and resets flags.