/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTimeSorter.h"
#include "../GateHelpers.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <G4Threading.hh>
#include <memory>
#include <utility>

// Static variable that allows a time sorter to determine whether it is the most
// upstream time sorter instance in the sequence of actors in the simulation.
std::atomic<GateTimeSorter *> GateTimeSorter::sMostUpstreamInstance{nullptr};

GateTimeSorter::GateTimeSorter(const std::string &name) : fName(name) {
  fNumWorkingThreads =
      std::max(1, G4Threading::GetNumberOfRunningWorkerThreads());
  fNumActiveWorkingThreads.store(fNumWorkingThreads);
  fMaxGlobalTimePerThread =
      std::make_unique<PaddedAtomicDouble[]>(fNumWorkingThreads);
}

GateTimeSorter::~GateTimeSorter() {
  // Reset the static so that subsequent simulation runs can elect a new
  // upstream instance. Without this, sMostUpstreamInstance would keep pointing
  // to a destroyed object and the compare-and-swap (CAS) in IsFirstUpstream()
  // would never succeed again (expected == nullptr would always fail).
  GateTimeSorter *expected = this;
  sMostUpstreamInstance.compare_exchange_strong(
      expected, nullptr, std::memory_order_acq_rel, std::memory_order_relaxed);
}

void GateTimeSorter::Init(GateDigiCollection *input) {

  fInputCollection = input;
  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto name = fInputCollection->GetName();

  // Create digi collections.

  // All collections are created with shared storage because digis originating
  // from different threads need to be time-sorted together.

  fIngestionBufferA = manager->NewDigiCollection(name + "_bufferA");
  fIngestionBufferA->InitDigiAttributesFromCopy(fInputCollection);
  fIngestionBufferA->SetSharedStorage(true);

  fIngestionBufferB = manager->NewDigiCollection(name + "_bufferB");
  fIngestionBufferB->InitDigiAttributesFromCopy(fInputCollection);
  fIngestionBufferB->SetSharedStorage(true);

  fSortedCollectionA = manager->NewDigiCollection(name + "_sortedA");
  fSortedCollectionA->InitDigiAttributesFromCopy(fInputCollection);
  fSortedCollectionA->SetSharedStorage(true);
  fSortedIndicesA.reset(new TimeSortedIndices);

  fSortedCollectionB = manager->NewDigiCollection(name + "_sortedB");
  fSortedCollectionB->InitDigiAttributesFromCopy(fInputCollection);
  fSortedCollectionB->SetSharedStorage(true);
  fSortedIndicesB.reset(new TimeSortedIndices);

  fOutputCollection = manager->NewDigiCollection(name + "_sortedOut");
  fOutputCollection->InitDigiAttributesFromCopy(fInputCollection);
  fOutputCollection->SetSharedStorage(true);

  // Iterator for enabling actors to obtain the time-sorted digis.
  fOutputIter = fOutputCollection->NewIterator();

  // Create fillers for copying digis from/to the various collections and store
  // them in a map.

  const auto attribute_names = fInputCollection->GetDigiAttributeNames();

  fFillers[{fInputCollection, fIngestionBufferA}] =
      std::make_unique<GateDigiAttributesFiller>(
          fInputCollection, fIngestionBufferA, attribute_names);
  fFillers[{fInputCollection, fIngestionBufferB}] =
      std::make_unique<GateDigiAttributesFiller>(
          fInputCollection, fIngestionBufferB, attribute_names);

  fFillers[{fIngestionBufferA, fSortedCollectionA}] =
      std::make_unique<GateDigiAttributesFiller>(
          fIngestionBufferA, fSortedCollectionA, attribute_names);
  fFillers[{fIngestionBufferB, fSortedCollectionA}] =
      std::make_unique<GateDigiAttributesFiller>(
          fIngestionBufferB, fSortedCollectionA, attribute_names);
  fFillers[{fIngestionBufferA, fSortedCollectionB}] =
      std::make_unique<GateDigiAttributesFiller>(
          fIngestionBufferA, fSortedCollectionB, attribute_names);
  fFillers[{fIngestionBufferB, fSortedCollectionB}] =
      std::make_unique<GateDigiAttributesFiller>(
          fIngestionBufferB, fSortedCollectionB, attribute_names);

  fFillers[{fSortedCollectionA, fOutputCollection}] =
      std::make_unique<GateDigiAttributesFiller>(
          fSortedCollectionA, fOutputCollection, attribute_names);
  fFillers[{fSortedCollectionB, fOutputCollection}] =
      std::make_unique<GateDigiAttributesFiller>(
          fSortedCollectionB, fOutputCollection, attribute_names);

  fInitialized = true;
}

void GateTimeSorter::SetSortingWindow(double duration) {
  // The sorting window, specified in nanoseconds, is the difference in
  // GlobalTime between the oldest and newest digi being stored, before they are
  // transferred to the output collection. Since the GlobalTime of incoming
  // digis is not guaranteed to increase monotonically, the sorting window must
  // be large enough to ensure that all digis can be properly time-sorted.
  // Non-monotonicity of GlobalTime can be caused by
  // * the time difference between a particle's generation and its interaction
  //   with a detector
  // * an upstream DigitizerBlurringActor with blur_attribute "GlobalTime"
  // * differences in GlobalTime between working threads in case of a
  //   multi-threaded simulation
  // The provided duration is used as the minimum size of the sorting window. In
  // multi-threaded simulations, the sorting window is automatically extended to
  // adapt to diverging GlobalTime values in the working threads.

  if (fProcessingStarted) {
    Fatal(
        "SetSortingWindow() cannot be called after Ingest() has been called.");
  }
  fMinimumSortingWindow = duration;
  fSortingWindow.store(duration);
}

void GateTimeSorter::SetMaxSize(size_t maxSize) {
  // Sets the maximum size of the output digi collection. Output digis that have
  // been consumed downstream will remain in the output collection until the
  // maximum size of the output collection is reached and the output collection
  // is cleared. Smaller maxSize values result in more frequent output
  // collection clearing, hence lower memory consumption.
  if (fProcessingStarted) {
    Fatal("SetMaxSize() cannot be called after Ingest() has been called.");
  }
  fMaxSize = maxSize;
}

void GateTimeSorter::SetBufferThreadSyncThreshold(size_t size) {
  if (fProcessingStarted) {
    Fatal("SetBufferThreadSyncThreshold() cannot be called after Ingest() has "
          "been called.");
  }
  fThreadSync.activationThreshold = size;
}

void GateTimeSorter::SetThreadSyncEnabled(bool enabled) {
  if (fProcessingStarted) {
    Fatal("SetThreadSyncEnabled() cannot be called after Ingest() has "
          "been called.");
  }
  fThreadSync.enabled = enabled;
}

void GateTimeSorter::OnEndOfEventAction(std::function<void(void)> work) {
  // This method is intended to be called by an actor in its EndOfEventAction()
  // method. The work function provided by the actor may then be called for
  // downstream processing of the time-sorted digis.
  // There are three stages:
  // 1. The time sorter ingests the digis that are provided by the actor by
  // copying them into an ingestion buffer. This ingestion must be synchronized
  // with a mutex, because all threads must copy their digis sequentially into
  // the same buffer.
  // 2. From time to time, the threads in a multi-threaded simulation require
  // synchronization to reduce memory consumption in the time sorter.
  // 3. The actual time-sorting, followed by the work provided by the actor,
  // happens next when a certain number of ingestions has happened since the
  // previous time sorting. This condition avoid incurring the overhead of stage
  // 3 after every ingestion of (typically very few) digis.

  // Phase 1

  if (!Ingest()) {
    // Return early if no digis were ingested.
    return;
  }

  // Phase 2

  // GlobalTime divergence between threads leads to increased memory consumption
  // in the time sorter. A thread synchronization barrier reduces GlobalTime
  // divergence by occasionally forcing the faster progressing threads to wait
  // for the slower ones to catch up. The thread synchronization should be
  // active in only one time sorter instance, to avoid deadlock. It should be
  // active in the most upstream time sorter instance, since only there the
  // GlobalTime observed by a thread is related to the primary events simulated
  // by that same thread (digis may switch from one thread's input collection to
  // another thread's output collection while being processed in the time
  // sorter). The first time sorter to ingest at least one digi will be marked
  // as the most upstream time sorter.

  if (ThreadSyncRequired()) {
    SetupBarrierIfNeeded();
    WaitAtBarrierIfNeeded();
  }

  // Phase 3

  // If the number of ingestions has not yet reached the threshold, then
  // increment the counter and return.
  constexpr int numIngestionsPerProcessCall = 10;
  // fetch_add() returns the value before the addition.
  if (fNumIngestions.fetch_add(1, std::memory_order_relaxed) <
      numIngestionsPerProcessCall - 1) {
    return;
  }

  // Number of ingestions has reached the threshold: subtract the threshold
  // value and continue.
  fNumIngestions.fetch_sub(numIngestionsPerProcessCall,
                           std::memory_order_relaxed);

  // First check that no other thread is currently busy processing.
  if (!fProcessingOngoing.load(std::memory_order_relaxed)) {
    bool expected = false;
    // If not, attempt to set the processing flag and continue if successful.
    if (fProcessingOngoing.compare_exchange_strong(expected, true,
                                                   std::memory_order_acquire,
                                                   std::memory_order_relaxed)) {
      Process(); // executes time-sorting logic
      if (ThreadSyncRequired()) {
        fThreadSync.sortedIndicesSize.store(fSortedIndicesA->size(),
                                            std::memory_order_release);
        fThreadSync.barrierSetupAllowed.store(true, std::memory_order_release);
      }
      work(); // executes the work provided by the actor
      fProcessingOngoing.store(false, std::memory_order_release);
    }
  }
}

void GateTimeSorter::OnEndOfRunAction(
    std::function<void(void)> anyThreadWork,
    std::function<void(void)> lastThreadWork) {
  // This method is intended to be called by an actor in its EndOfRunAction()
  // method. The calling actor provides a first function to be executed on any
  // thread that calls OnEndOfRunAction. The second function provided is
  // executed only by the last remaining thread, before the execution of
  // anyThreadWork.
  // lastThreadWork allows the calling actor to execute logic that is intended
  // to run after the GateTimeSorter has finalized all digi sorting.

  if (ThreadSyncRequired()) {
    // Disable thread synchronization at the end of a run.
    fThreadSync.barrierBypassed.store(true, std::memory_order_release);
    fThreadSync.barrierConditionVariable.notify_all();
  }
  if (fNumActiveWorkingThreads.fetch_sub(1, std::memory_order_acq_rel) <= 1) {
    Process();
    Flush();
    lastThreadWork();
  }
  anyThreadWork();
}

GateDigiCollection *GateTimeSorter::OutputCollection() const {
  // Provides access to the output digi collection for downstream processing.
  return fOutputCollection;
}

GateDigiCollection::Iterator &GateTimeSorter::OutputIterator() {
  // Provides access to the output iterator, which automatically keeps track of
  // previously processed sorted digis.
  return fOutputIter;
}

void GateTimeSorter::MarkOutputAsProcessed() {
  // Modifies the index of the output iterator, to ensure that future use of the
  // iterator starts with the output digis that have not been processed yet.
  // Once in a while, the output collection is cleared to reduce memory
  // consumption (cfr. Prune()).
  if (fOutputCollection->GetSize() <= fMaxSize) {
    fOutputCollection->SetBeginOfEventIndex(fOutputIter.fIndex);
  } else {
    fOutputCollection->Clear();
    fOutputIter.Reset();
  }
}

bool GateTimeSorter::Ingest() {
  // Locks the mutex and copies all digis from the input collection into
  // ingestion buffer A. Remembers the highest GlobalTime value observed so far
  // for the current thread.
  if (fFlushed) {
    Fatal("Ingest() called after Flush(). The time sorter must not be used "
          "after it was flushed.");
  }
  G4AutoLock lock(&fIngestionMutex);

  fProcessingStarted = true;

  // Create an iterator that tracks GlobalTime.
  auto iter = fInputCollection->NewIterator();
  double *t;
  iter.TrackAttribute("GlobalTime", &t);

  iter.GoToBegin();

  if (iter.IsAtEnd()) {
    // The event has no digis.
    return false;
  }

  // Look up the appropriate filler.
  auto filler = fFillers[{fInputCollection, fIngestionBufferA}].get();

  // Copy digis while keeping track of the maximum GlobalTime value.
  const int tid = std::max(0, G4Threading::G4GetThreadId());
  const double currentMax = fMaxGlobalTimePerThread[tid].value.load();
  double newMax = currentMax;
  while (!iter.IsAtEnd()) {
    filler->Fill(iter.fIndex);
    newMax = std::max(newMax, *t);
    iter++;
  }

  // In case of a multi-threaded simulation, extend the sorting time if needed,
  // depending on the GlobalTime difference between the slowest and fastest
  // progressing working thread.
  if (fNumWorkingThreads > 1 && newMax > currentMax) {
    fMaxGlobalTimePerThread[tid].value.store(newMax);
    auto [minIt, maxIt] = std::minmax_element(
        fMaxGlobalTimePerThread.get(),
        fMaxGlobalTimePerThread.get() + fNumWorkingThreads,
        [](const PaddedAtomicDouble &a, const PaddedAtomicDouble &b) {
          return a.value.load() < b.value.load();
        });
    fSortingWindow.store(std::max(fSortingWindow.load(),
                                  fMinimumSortingWindow + maxIt->value.load() -
                                      minIt->value.load()));
  }

  return true;
}

bool GateTimeSorter::IsFirstUpstream() {
  // The most upstream time sorter is the one that has succeeded in replacing
  // the nullptr value with its own this pointer.
  if (fIsFirstUpstream.load(std::memory_order_relaxed)) {
    return true;
  }
  // Once any instance is elected, there is no point retrying the CAS.
  if (sMostUpstreamInstance.load(std::memory_order_relaxed) != nullptr) {
    return false;
  }
  // Try to replace nullptr by the this pointer value and return true if it
  // succeeded.
  GateTimeSorter *expected = nullptr;
  if (sMostUpstreamInstance.compare_exchange_strong(
          expected, this, std::memory_order_acq_rel,
          std::memory_order_relaxed)) {
    fIsFirstUpstream.store(true, std::memory_order_release);
    return true;
  }
  return false;
}

bool GateTimeSorter::ThreadSyncRequired() {
  return fNumWorkingThreads > 1 && fThreadSync.enabled && IsFirstUpstream();
}

void GateTimeSorter::SetupBarrierIfNeeded() {
  // * barrierSetupAllowed: set to true as soon as Process() has been executed
  //     after all threads have reached the barrier, indicating that
  //     sortedIndicesSize has been reduced.
  // * barrierSetupClaimed: ensures that only one thread can set up the barrier.
  // * barrierSetupComplete: indicates that the barrier is active.

  auto &ts = fThreadSync;
  // As soon as the number of buffered digis reaches the activation threshold,
  // one thread activates the barrier.
  if (ts.barrierSetupAllowed.load(std::memory_order_relaxed) &&
      !ts.barrierSetupClaimed.load(std::memory_order_relaxed) &&
      ts.sortedIndicesSize.load(std::memory_order_relaxed) >=
          fThreadSync.activationThreshold) {
    bool expected = false;
    if (ts.barrierSetupClaimed.compare_exchange_strong(
            expected, true, std::memory_order_acq_rel,
            std::memory_order_relaxed)) {
      // Determine the highest GlabalTime value across all threads.
      auto maxIt = std::max_element(
          fMaxGlobalTimePerThread.get(),
          fMaxGlobalTimePerThread.get() + fNumWorkingThreads,
          [](const PaddedAtomicDouble &a, const PaddedAtomicDouble &b) {
            return a.value.load() < b.value.load();
          });
      // Store target before the release on fBarrierSetupComplete so that
      // threads that acquire fBarrierSetupComplete == true are guaranteed
      // to see it.
      const double maxTime = maxIt->value.load();
      ts.barrierGlobalTimeTarget.store(maxTime, std::memory_order_relaxed);
      ts.barrierSetupComplete.store(true, std::memory_order_release);
    }
  }
}

void GateTimeSorter::WaitAtBarrierIfNeeded() {
  auto &ts = fThreadSync;
  // If the barrier has been set up and this thread's GlobalTime has reached
  // the current target value, then wait until every other thread has also
  // reached it.
  if (ts.barrierSetupComplete.load(std::memory_order_acquire)) {
    const int tid = std::max(0, G4Threading::G4GetThreadId());
    const double threadTime =
        fMaxGlobalTimePerThread[tid].value.load(std::memory_order_relaxed);
    const double targetTime =
        ts.barrierGlobalTimeTarget.load(std::memory_order_acquire);

    if (threadTime >= targetTime) {
      std::unique_lock<std::mutex> cvLock(ts.barrierConditionVariableMutex);

      // Re-check under lock: the barrier may have been released while we
      // were between the outer fBarrierSetupComplete check and here.
      if (ts.barrierSetupComplete.load(std::memory_order_relaxed)) {
        const int generation =
            ts.barrierGeneration.load(std::memory_order_relaxed);
        const int numArrived =
            ts.numThreadsAtBarrier.fetch_add(1, std::memory_order_relaxed) + 1;

        if (numArrived >= fNumWorkingThreads) {
          // Last thread to arrive: reset state and release all waiters.
          ts.numThreadsAtBarrier.store(0, std::memory_order_relaxed);
          ts.barrierSetupComplete.store(false, std::memory_order_relaxed);
          ts.barrierSetupClaimed.store(false, std::memory_order_relaxed);
          ts.barrierSetupAllowed.store(false, std::memory_order_relaxed);

          // Reset sorting window to allow number of buffered digis to decrease
          // in the next call to Process().  Do this before unlocking so woken
          // threads see the updated value during Process().
          auto [minIt, maxIt] = std::minmax_element(
              fMaxGlobalTimePerThread.get(),
              fMaxGlobalTimePerThread.get() + fNumWorkingThreads,
              [](const PaddedAtomicDouble &a, const PaddedAtomicDouble &b) {
                return a.value.load() < b.value.load();
              });
          fSortingWindow.store(fMinimumSortingWindow + maxIt->value.load() -
                               minIt->value.load());

          ts.barrierGeneration.fetch_add(1, std::memory_order_relaxed);
          cvLock.unlock();
          // Last thread has arrived so all can resume their work.
          ts.barrierConditionVariable.notify_all();
        } else {
          // Park the thread until the barrier is released or the run ends.
          // cvLock is already held; wait() releases it while parked.
          ts.barrierConditionVariable.wait(cvLock, [&] {
            return ts.barrierGeneration.load(std::memory_order_relaxed) !=
                       generation ||
                   ts.barrierBypassed.load(std::memory_order_relaxed);
          });
        }
      }
    }
  }
}

void GateTimeSorter::Process() {
  // Processes all digis from the ingestion buffer by copying and sorting them
  // according to GlobalTime. Next, copies the oldest sorted digis to the
  // output collection, taking into account the value of the sorting time.

  if (fFlushed) {
    Fatal("Process() called after Flush(). The time sorter must not be used "
          "after it was flushed.");
  }

  // First, swap the pointers to ingestion buffers A and B while the mutex is
  // locked. After the swap, the digis in buffer B can be processed downstream,
  // while the now empty buffer A can be used by other threads for ingesting new
  // digis.
  {
    G4AutoLock lock(&fIngestionMutex);
    std::swap(fIngestionBufferA, fIngestionBufferB);
    fIngestionBufferA->Clear();
  }

  // From here onwards, it is safe to process the contents of ingestion buffer B
  // downstream, because OnEndOfEventAction() guarantees that only one thread
  // can ever be executing Process() at the same time, and only Process() can
  // swap the buffer pointers.

  // Return early if there are no digis to process.
  if (fIngestionBufferB->GetSize() == 0) {
    return;
  }

  // Look up the fillers needed to copy the digis from ingestion buffer to
  // sorted collection, and from sorted collection to output collection.
  auto fillerIn = fFillers[{fIngestionBufferB, fSortedCollectionA}].get();
  auto fillerOut = fFillers[{fSortedCollectionA, fOutputCollection}].get();

  // Create an iterator for ingestion buffer B that tracks GlobalTime.
  auto iter = fIngestionBufferB->NewIterator();
  double *t;
  iter.TrackAttribute("GlobalTime", &t);

  // Start sorting.
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    const size_t digiIndex = fSortedCollectionA->GetSize();
    const double digiTime = *t;
    fNumDigi++;
    // If a digi is older (lower GlobalTime value) than the newest digi that has
    // already been transferred to the output collection, then this digi must be
    // dropped to be able to guarantee time-monotonicity in the output
    // collection.
    // The automatic extension of the sorting window should be adequate to
    // ensure that no digi is ever dropped, but in case it does happen, it will
    // be logged so that the user is warned to use SetSortingWindow() to
    // increase its size.
    if (fMostRecentTimeDeparted.has_value() &&
        (digiTime < *fMostRecentTimeDeparted)) {
      ++fNumDroppedDigi;
      fMaxDropDelta =
          std::max(fMaxDropDelta, *fMostRecentTimeDeparted - digiTime);
      if (!fSortingWindowWarningIssued) {
        std::cout << "The digis output by actor '"
                  << fInputCollection->GetName()
                  << "' have non-monotonicities in the GlobalTime attribute "
                     "that exceed the sorting time in actor '"
                  << fName << "' (" << fMinimumSortingWindow << " ns).\n";
        fSortingWindowWarningIssued = true;
      }
    } else {
      // Copy the digi into the "sorted" collection A. This collection is not
      // really sorted by itself (digis are still in the same order as they were
      // in the ingestion buffer), but the collection is accompanied by a
      // std::priority_queue (fSortedIndicesA) which time-sorts indices of the
      // digis.
      fillerIn->Fill(iter.fIndex);
      fSortedIndicesA->push({digiIndex, digiTime});

      // Keep track of the highest GlobalTime observed so far across all
      // threads.
      if (!fMostRecentTimeArrived || (digiTime > *fMostRecentTimeArrived)) {
        fMostRecentTimeArrived = digiTime;
      }
    }
    iter++;
  }

  // Copy the oldest time-sorted digis into the output
  // collection. Continue as long as the newest digi is at least
  // fSortingWindow more recent than the oldest digi. This guarantees
  // time-monotonicity in the output collection.
  while (!fSortedIndicesA->empty() &&
         (*fMostRecentTimeArrived - fSortedIndicesA->top().time >
          fSortingWindow.load())) {
    // Copy oldest digi into the output collection.
    fillerOut->Fill(fSortedIndicesA->top().index);
    // Keep track of the GlobalTime of the last digi that was copied.
    fMostRecentTimeDeparted = fSortedIndicesA->top().time;
    // Remove the time-sorted index of the digi.
    fSortedIndicesA->pop();
  }

  // The sorted digi collection keeps growing as more digis are processed.
  // The digis that have already been copied to the output must be removed
  // once in a while to limit memory usage.
  constexpr size_t n1 = 100'000;
  constexpr size_t n2 = 1'000'000;
  // n is the number of digis that can be removed.
  const size_t n = fSortedCollectionA->GetSize() - fSortedIndicesA->size();
  // Pruning removes digis that can be removed, and copies the others.
  // So make sure to not do this too frequently, otherwise the memory gain is
  // low and the time required for copying is relatively high.
  if ((n >= n1 && n >= fSortedCollectionA->GetSize() / 2) || n >= n2) {
    Prune();
  }
}

void GateTimeSorter::Flush() {
  // Copies all remaining sorted digis into the output collection.
  // This method is intended to be called once at the end of time sorting,
  // when it is known that no more digis will be processed from the input. As
  // a consequence, the sorting window does not have to be taken into account
  // while flushing.
  auto fillerOut = fFillers[{fSortedCollectionA, fOutputCollection}].get();
  while (fSortedIndicesA->size() > 0) {
    fillerOut->Fill(fSortedIndicesA->top().index);
    fSortedIndicesA->pop();
  }
  Prune();
  fFlushed = true;
  if (fNumDroppedDigi > 0) {
    const auto percentage =
        static_cast<double>(fNumDroppedDigi) / fNumDigi * 100;
    std::cout << fNumDroppedDigi << " digis (" << percentage
              << " %) have been dropped while time-sorting in actor '" << fName
              << "'. Please increase the sorting time to a value higher than "
                 "the current "
              << fMinimumSortingWindow << " ns (suggestion: > " << fMaxDropDelta
              << "ns)\n";
  }
}

void GateTimeSorter::Prune() {
  // Frees memory that is currently occupied by digis that have already been
  // copied into the output collection:
  // 1. The digis that have not been copied to the output yet, are copied from
  // sorted collection A into sorted collection B.
  // 2. Sorted collection A is cleared.
  // 3. The two collections and sorted index queues are swapped.

  // Step 1
  GateDigiAttributesFiller transferFiller(
      fSortedCollectionA, fSortedCollectionB,
      fSortedCollectionA->GetDigiAttributeNames());
  while (!fSortedIndicesA->empty()) {
    // Take the next sorted index from A.
    const auto timedIndex = fSortedIndicesA->top();
    fSortedIndicesA->pop();
    // Create a new sorted index for B.
    const size_t digiIndex = fSortedCollectionB->GetSize();
    const double digiTime = timedIndex.time;
    // Copy the digi from A to B.
    transferFiller.Fill(timedIndex.index);
    // Sort the new index.
    fSortedIndicesB->push({digiIndex, digiTime});
  }

  // Step 2
  fSortedCollectionA->Clear();

  // Step 3
  std::swap(fSortedCollectionA, fSortedCollectionB);
  std::swap(fSortedIndicesA, fSortedIndicesB);
}
