Coincidence Detection in Multi-Threaded Simulations
====================================================

This document describes the design of ``GateTimeSorter`` and
``GateCoincidenceSorterActor`` and how they cooperate to perform coincidence
detection in a multi-threaded GATE simulation.  It targets GATE developers
who want to understand, extend, or debug this subsystem.


Problem Statement
-----------------

In a multi-threaded simulation each worker thread runs an independent
event loop and produces its own per-thread digi stream.  Those streams are
**not globally time-sorted**: a single ``EndOfEventAction`` call on thread *A*
may produce digis with a lower ``GlobalTime`` than digis that were produced
moments earlier on thread *B*.

Coincidence detection requires a **single, globally time-ordered digi stream**
because a coincidence pair may consist of two singles originating from primary
events simulated in *different threads* (random coincidences).
Such a pair will never be found by an algorithm that only inspects one thread's
output at a time.

``GateTimeSorter`` solves this by merging all per-thread digi streams into one
time-sorted stream.  ``GateCoincidenceSorterActor`` consumes that stream to
identify coincidence pairs.


Component Overview
------------------

``GateTimeSorter`` (``GateTimeSorter.h/.cpp``)
    A self-contained merge-sorter.  It is not a GATE actor but a helper object
    owned by ``GateCoincidenceSorterActor``.  It manages several internal digi
    collections (see `Data-Flow Diagram`_) and exposes three operations that
    callers use via the higher-level wrappers ``OnEndOfEventAction()`` and
    ``OnEndOfRunAction()``:

    * ``Ingest()``  — copies the calling thread's digis into a shared
      ingestion buffer.  Always mutex-protected; deliberately minimal.
    * ``Process()`` — sorts the buffered digis and drains the oldest ones to
      the output collection.  Only one thread executes this at a time, and
      only the thread currently tracking the highest ``GlobalTime`` is
      selected (see `Phase 2 — Sorting and Output`_).
    * ``Flush()``   — drains all remaining sorted digis at end-of-run,
      without applying the sorting window.

``GateCoincidenceSorterActor`` (``GateCoincidenceSorterActor.h/.cpp``)
    A standard GATE actor.  In ``EndOfEventAction`` it passes a lambda to
    ``OnEndOfEventAction()``.  The time sorter first calls ``Ingest()`` and,
    when conditions are met, calls ``Process()`` followed by the lambda.
    The lambda calls ``ProcessTimeSortedSingles()`` (copies new time-sorted
    digis into a local temporary storage) and ``DetectCoincidences()``
    (scans that storage for coincidence pairs and writes them to the output
    collection).


Data-Flow Diagram
-----------------

Solid arrows show the forward data path.  Dashed arrows (``- ->``) show
memory-reclamation paths.

.. code-block:: text

    +------------------ GateTimeSorter ----------------------------------+
    |                                                                    |
    |  Thread 0    Thread 1   ...   Thread N                             |
    |      |           |                |                                |
    |      +--------- Ingest() [mutex] -+                                |
    |                       |                                            |
    |                       v                                            |
    |               fIngestionBufferA  <-- all threads write here        |
    |                       |                                            |
    |          [buffer swap under mutex, inside Process()]               |
    |                       |                                            |
    |                       v                                            |
    |               fIngestionBufferB  <-- read only by Process()        |
    |                       |                                            |
    |              [sort into min-heap]                                  |
    |                       |                                            |
    |                       v                                            |
    |   fSortedCollectionA + fSortedIndicesA (min-heap)                  |
    |                       |                                            |
    |    [drain: most-recently-arrived time - oldest queued time         |
    |            > fSortingWindow]                                       |
    |                       |                                            |
    |                       v                                            |
    |               fOutputCollection                                    |
    |                                                                    |
    |   - - Memory reclamation (Prune): - -                              |
    |   surviving digis: fSortedCollectionA - -> fSortedCollectionB,    |
    |   fSortedCollectionA cleared, fSortedCollectionA <-> B swapped    |
    |                                                                    |
    +------------------------------+-------------------------------------+
                                   |
                   ProcessTimeSortedSingles()
                                   |
    +------- GateCoincidenceSorterActor ---------------------------------+
    |                              |                                     |
    |                              v                                     |
    |        TemporaryStorage::digis (fCurrentStorage)                   |
    |                              |                                     |
    |                   DetectCoincidences()                             |
    |                              |                                     |
    |                              v                                     |
    |            Coincidence output collection                           |
    |                                                                    |
    |   - - Memory reclamation (ClearProcessedSingles): - -              |
    |   unprocessed digis: fCurrentStorage - -> fFutureStorage,         |
    |   fCurrentStorage cleared, fCurrentStorage <-> fFutureStorage     |
    |   swapped                                                          |
    +--------------------------------------------------------------------+


GateTimeSorter: Design and Threading Model
------------------------------------------

Phase 1 — Ingestion
^^^^^^^^^^^^^^^^^^^

Every call to ``OnEndOfEventAction()`` begins with ``Ingest()``.  Under the
protection of ``fIngestionMutex``, ``Ingest()``:

1. Iterates over all digis in the calling thread's input collection.
2. Copies each digi into ``fIngestionBufferA`` via a pre-built
   ``GateDigiAttributesFiller``.
3. Updates ``fMaxGlobalTimePerThread[tid]``, a cache-line-padded atomic
   ``double`` (``PaddedAtomicDouble``) indexed by thread ID, to record the
   highest ``GlobalTime`` value seen by this thread so far.

The critical section is intentionally minimal: a sequential copy of a
typically small batch of digis, no sorting, no downstream processing.
Threads therefore block each other for only a very short time.


Phase 2 — Sorting and Output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After returning from ``Ingest()``, ``OnEndOfEventAction()`` increments the
shared counter ``fNumIngestions`` (a relaxed atomic) and returns early unless
the counter has reached the threshold ``numIngestionsPerProcessCall`` (= 10).
This throttle avoids the overhead of sorting after every single ingestion.

Once the threshold is reached, the thread attempts to become the exclusive
processor by performing a compare-and-swap (CAS) on ``fProcessingOngoing``:

.. code-block:: cpp

    bool expected = false;
    fProcessingOngoing.compare_exchange_strong(
        expected, true,
        std::memory_order_acquire,   // success ordering
        std::memory_order_relaxed);  // failure ordering

If the CAS fails — either because another thread already holds the token or
the preliminary relaxed load showed it was taken — the calling thread simply
returns and continues simulating.  It is never blocked.

If the CAS succeeds, the thread checks whether it is the one currently
tracking the highest ``GlobalTime``:

.. code-block:: cpp

    if (tid == fFastestThread.load()) {
        Process();
        work();   // actor lambda: ProcessTimeSortedSingles + DetectCoincidences
    }
    fProcessingOngoing.store(false, std::memory_order_release);

A thread that wins the CAS but is *not* the fastest one releases the token
immediately without calling ``Process()``.  The intent is that sorting work
migrates to whichever thread is furthest ahead in simulation time: the fastest
thread occasionally pauses to do sorting and coincidence detection work,
which gives the slower threads time to catch up, reducing ``GlobalTime``
divergence.

Inside ``Process()``:

1. **Buffer swap (under mutex).** ``fIngestionBufferA`` and
   ``fIngestionBufferB`` are pointer-swapped and the newly designated
   ``fIngestionBufferA`` is cleared.  This is the only point in
   ``Process()`` where ``fIngestionMutex`` is held.  After the mutex is
   released, other threads can immediately resume ingesting into the cleared
   buffer, while ``Process()`` owns the data in ``fIngestionBufferB``
   exclusively (see `Exclusive Ownership of fIngestionBufferB After the Swap`_).

2. **Sorting-window extension.** In multi-threaded mode the sorting window
   is extended if the current thread spread requires it (see
   `The Sorting Window`_).

3. **Sort.** Digis from ``fIngestionBufferB`` are iterated in arrival order.
   Each digi is appended to ``fSortedCollectionA`` and its (index, time) pair
   is pushed onto the min-heap ``fSortedIndicesA``.  The heap thereby provides
   a globally time-sorted view of all digis ingested so far.

4. **Drain.** Digis are popped from the heap and copied to
   ``fOutputCollection`` as long as::

       fMostRecentTimeArrived - fSortedIndicesA.top().time > fSortingWindow

   This *sorting window guarantee* ensures time-monotonicity in the output
   stream: no future ingestion can produce a digi with a low enough
   ``GlobalTime`` to be inserted before anything already drained.

5. **Fastest-thread re-evaluation.** Because the current thread has been
   doing sorting and coincidence detection work since it was identified
   as the fastest, it may no longer hold that distinction.
   ``IdentifyFastestThread()`` refreshes ``fFastestThread`` so that
   subsequent processing calls are routed to the correct thread.


The Sorting Window
^^^^^^^^^^^^^^^^^^

``GlobalTime`` in the input stream is not guaranteed to increase
monotonically.  Sources of non-monotonicity include:

* the travel time of a secondary particle from its creation point to the
  detector,
* an upstream ``DigitizerBlurringActor`` with ``blur_attribute="GlobalTime"``,
* ``GlobalTime`` divergence between worker threads.

``fSortingWindow`` is the minimum ``GlobalTime`` gap required between the
oldest unsorted digi and the most recently arrived digi before the oldest
digi is considered safe to emit.  A user-specified minimum
``fMinimumSortingWindow`` provides the baseline.  In multi-threaded mode the
window is automatically extended to cover the current spread of ``GlobalTime``
across all threads:

.. code-block:: text

    fSortingWindow = max(fSortingWindow,
                         fMinimumSortingWindow
                         + max(fMaxGlobalTimePerThread)
                         - min(fMaxGlobalTimePerThread))

The window grows monotonically and never shrinks, so a temporary burst of
thread divergence leaves a permanent safety margin.


End of Run — Flush
^^^^^^^^^^^^^^^^^^

``OnEndOfRunAction()`` atomically decrements ``fNumActiveWorkingThreads``.
The thread that takes the counter to zero is the last active worker; it calls
``Process()`` and ``Flush()``, which drains all remaining digis from
``fSortedIndicesA`` into ``fOutputCollection`` without applying the sorting
window, since no further digis will arrive.
It then calls ``lastThreadWork()``.  Every thread subsequently calls
``anyThreadWork()``.  Before ``OnEndOfRunAction()`` returns,
each thread calls ``MarkThreadAsFinished()``, which zeroes its
``fMaxGlobalTimePerThread`` entry so it is no longer eligible to be selected
as the fastest thread.


Correctness of the Lock-Free Processing Path
---------------------------------------------

After the buffer swap inside ``Process()``, the remainder of that function
reads and writes ``fIngestionBufferB``, ``fSortedCollectionA``,
``fSortedIndicesA``, ``fOutputCollection``, ``fMostRecentTimeArrived``,
``fMostRecentTimeDeparted``, ``fSortingWindow``, and ``fFastestThread``
**without holding any mutex**.  This section explains why that is safe.


Exclusive Ownership of ``fIngestionBufferB`` After the Swap
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Process()`` is the only function that swaps ``fIngestionBufferA`` and
``fIngestionBufferB``.  After the swap (performed under ``fIngestionMutex``):

* ``fIngestionBufferA`` now points to the previously empty buffer.  All
  subsequent ``Ingest()`` calls will write there, because ``Ingest()`` looks
  up its filler using the *current pointer value* of ``fIngestionBufferA`` as
  the map key — the lookup therefore automatically redirects to the newly
  designated ingestion buffer.
* ``fIngestionBufferB`` now points to the buffer that held the accumulated
  digis.  No other code path writes to this buffer until the *next* call to
  ``Process()``.

The mutex release inside ``Process()`` happens-before the mutex acquire inside
the next ``Ingest()`` call, guaranteeing that every subsequent ``Ingest()``
observes the post-swap pointer values and writes into the correct buffer.


Serialisation of ``Process()`` Invocations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The CAS on ``fProcessingOngoing`` acts as a lightweight, spinless critical
section around the body of ``Process()``:

* The **acquire** ordering on a successful CAS establishes a happens-before
  relationship with the **release** store at the end of the *previous*
  ``Process()`` invocation.  All writes made by that invocation to
  ``fSortedCollectionA``, ``fSortedIndicesA``, ``fOutputCollection``,
  ``fMostRecentTimeArrived``, ``fMostRecentTimeDeparted``, ``fSortingWindow``,
  and ``fFastestThread`` are therefore visible to the current invocation,
  even though no mutex guards those fields directly.
* The **release** store at the end of ``Process()`` makes all writes of the
  current invocation visible to the next thread that successfully acquires the
  token.

Because the CAS is an atomic read-modify-write, at most one thread can succeed
at a time, so all ``Process()`` invocations are globally serialised.

The actor lambda (``ProcessTimeSortedSingles`` and ``DetectCoincidences``) is
also serialised by this mechanism, because it is only ever called from within
the CAS-protected block.  The actor-side fields ``fCurrentStorage``,
``fFutureStorage``, and ``fIterPosition`` are therefore safe to access without
additional synchronisation.


Non-Processing Threads Are Never Blocked
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A thread that fails the CAS — or that wins it but is not the fastest thread
and immediately releases the token — returns from ``OnEndOfEventAction()``
and continues simulating without ever waiting on a lock or spinning.  The
entire fast path (ingestion counter increment → preliminary flag check → CAS
attempt → early return) is **wait-free**: it completes in a bounded number of
steps regardless of contention.


Visibility of ``fMaxGlobalTimePerThread``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``fMaxGlobalTimePerThread`` is an array of ``PaddedAtomicDouble`` values, each
padded to one cache-line (64 bytes) to prevent false sharing.  Each thread
writes only to its own element inside ``Ingest()``; ``Process()`` reads all
elements to compute the sorting window extension and to re-evaluate the fastest
thread.

Concurrent access is safe because:

* **Per-thread ownership of writes.** Each element is written by exactly one
  thread (its owner), so there are no write-write races.
* **Read ordering.** The reads in ``Process()`` happen after the acquire CAS
  and before the release store of ``fProcessingOngoing``.  All values written
  by any ``Ingest()`` call that completed before the previous
  ``Process()``-release-store are therefore visible.
* **Benign races on in-flight values.** ``Ingest()`` can run concurrently
  with ``Process()`` after the buffer swap.  A read in ``Process()`` may
  therefore see a value that is one ingestion stale.  This is harmless: the
  sorting window extension is conservative (a slightly underestimated spread
  is corrected in the next ``Process()`` call, and the window never shrinks)
  and fastest-thread selection is heuristic (routing to a slightly suboptimal
  thread does not affect correctness).


GateCoincidenceSorterActor: Consuming the Sorted Stream
-------------------------------------------------------

``BeginOfRunActionMasterThread`` creates and configures a ``GateTimeSorter``
(sorting window = ``fSortingTime``) and two ``TemporaryStorage`` objects
(``fCurrentStorage`` and ``fFutureStorage``).  Each ``TemporaryStorage`` holds
a ``GateDigiCollection`` of time-sorted singles together with the
``GlobalTime`` of the earliest and latest digi it currently contains.

At each ``EndOfEventAction``, the actor passes a lambda to
``fTimeSorter->OnEndOfEventAction()``.  When the time sorter decides that the
current thread should do processing, the lambda executes two steps:

**ProcessTimeSortedSingles()**
    Iterates over the new digis in ``fOutputCollection`` using
    ``fTimeSorter->OutputIterator()`` (which tracks the position of the last
    processed digi) and appends each digi to ``fCurrentStorage->digis``,
    updating ``earliestTime`` and ``latestTime``.  ``MarkOutputAsProcessed()``
    then advances the iterator so the same digis are not revisited.

**DetectCoincidences()**
    Scans ``fCurrentStorage->digis`` starting at ``fIterPosition`` (the first
    not-yet-processed single).  For each *opening single* at index ``i0`` with
    time ``t0`` it searches forward for singles whose ``GlobalTime`` falls in
    the coincidence window::

        [t0 + fWindowOffset,  t0 + fWindowOffset + fWindowSize]

    and whose detector volume (at depth ``fGroupVolumeDepth``) differs from
    that of the opening single.  Accepted coincidence pairs, after applying the
    configured ``MultiplesPolicy``, are written to the coincidence output
    collection.

    The outer loop terminates once the ``GlobalTime`` span currently held in
    ``fCurrentStorage`` is too small to guarantee that all possible coincidence
    partners of the current opening single have been seen — i.e., when::

        latestTime - earliestTime <= fWindowSize + fWindowOffset

    This condition ensures that ``DetectCoincidences()`` never emits a
    coincidence that is later found to be incomplete due to a missing single
    that had not yet arrived.

At ``EndOfRunAction``, ``OnEndOfRunAction`` ensures ``Flush()`` is called by
the last remaining thread.  The last-thread lambda then calls
``ProcessTimeSortedSingles`` followed by ``DetectCoincidences(true)`` (the
``lastCall = true`` argument relaxes the termination condition to drain all
remaining singles).


Thread Lifecycle Summary
------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 18 54

   * - Simulation phase
     - Thread
     - Actions and synchronisation
   * - ``BeginOfRunActionMasterThread``
     - Master only
     - Creates ``GateTimeSorter`` and ``TemporaryStorage`` A/B.  No mutex.
   * - ``EndOfEventAction``
     - All workers
     - ``Ingest()`` — acquires ``fIngestionMutex`` briefly (copy + atomic
       store to per-thread max).  Increment ``fNumIngestions`` (relaxed
       atomic).  If threshold reached: attempt CAS on ``fProcessingOngoing``
       (atomic, non-blocking).  If CAS succeeds and thread is fastest:
       ``Process()`` — acquires ``fIngestionMutex`` for buffer swap only,
       then fully lock-free — followed by actor lambda (lock-free).
   * - ``EndOfRunAction``
     - All workers
     - Decrement ``fNumActiveWorkingThreads`` (atomic).  Last thread:
       ``Flush()`` (single-threaded at this point) then ``lastThreadWork()``.
       All threads: ``anyThreadWork()``.  Each thread: ``MarkThreadAsFinished()``
       (atomic store).
