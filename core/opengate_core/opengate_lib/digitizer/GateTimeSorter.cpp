#include "GateTimeSorter.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <G4Threading.hh>
#include <memory>
#include <utility>

GateTimeSorter::GateTimeSorter() {
  fNumWorkingThreads =
      std::max(1, G4Threading::GetNumberOfRunningWorkerThreads());
  fNumActiveWorkingThreads.store(fNumWorkingThreads);
  fMaxGlobalTimePerThread =
      std::make_unique<PaddedAtomicDouble[]>(fNumWorkingThreads);
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

  fIngestionBufferB = manager->NewDigiCollection(name + "_bufferA");
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
  fSortingWindow = duration;
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

void GateTimeSorter::OnEndOfEventAction(std::function<void(void)> work) {
  // This method is intended to be called by an actor in its EndOfEventAction()
  // method. The work function provided by the actor may then be called for
  // downstream processing of the time-sorted digis.
  // There are two stages:
  // 1. The time sorter ingests the digis that are provided by the actor by
  // copying them into an ingestion buffer. This ingestion must be synchronized
  // with a mutex, because all threads must copy their digis sequentially into
  // the same buffer.
  // 2. The actual time-sorting, followed by the work provided by the actor,
  // happens next on two conditions: (i) a minimum number of ingestions
  // has happened since the previous time sorting, and (ii) the current thread
  // is the one with the most advanced GlobalTime value. If these conditions are
  // not fulfilled, the execution of stage 2 is postponed until a later
  // invocation of OnEndOfEventAction. These conditions avoid incurring the
  // overhead of stage 2 after every ingestion of (typically very few) digis and
  // make sure that the fastest progressing working threads do more work than
  // the slower ones, which reduces GlobalTime divergence between threads.

  // Phase 1

  Ingest();

  // Phase 2

  // If the number of ingestions has not yet reached the threshold, then
  // increment the counter and return.
  constexpr int numIngestionsPerProcessCall = 10;
  // fetch_add() returns the value before the addition.
  if (fNumIngestions.fetch_add(1, std::memory_order_relaxed) <
      numIngestionsPerProcessCall - 1) {
    return;
  }

  // Number of ingestions thas reached the threshold: subtract the threshold
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
      // If the current thread has been identified as the fastest progressing
      // one, then do the processing.
      const int tid = std::max(0, G4Threading::G4GetThreadId());
      if (tid == fFastestThread.load()) {
        Process(); // executes time-sorting logic
        work();    // executes the work provided by the actor
      }
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
  if (fNumActiveWorkingThreads.fetch_sub(1, std::memory_order_acq_rel) <= 1) {
    Flush();
    lastThreadWork();
  }
  anyThreadWork();
  MarkThreadAsFinished(std::max(0, G4Threading::G4GetThreadId()));
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

// CONTINUE HERE

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

void GateTimeSorter::Ingest() {
  // Locks the mutex and copies all digis from the input collection into
  // ingestion buffer A. Remembers the highest GlobalTime value observed so far
  // for the current thread.
  if (fFlushed) {
    Fatal("Ingest() called after Flush(). The time sorter must not be used "
          "after it was flushed.");
  }
  G4AutoLock lock(&fIngestionMutex);

  fProcessingStarted = true;

  // Look up the appropriate filler.
  auto filler = fFillers[{fInputCollection, fIngestionBufferA}].get();

  // Create an iterator that tracks GlobalTime.
  auto iter = fInputCollection->NewIterator();
  double *t;
  iter.TrackAttribute("GlobalTime", &t);

  // Copy digis while keeping track of the maximum GlobalTime value.
  iter.GoToBegin();
  const int tid = std::max(0, G4Threading::G4GetThreadId());
  const double currentMax = fMaxGlobalTimePerThread[tid].value.load();
  double newMax = currentMax;
  while (!iter.IsAtEnd()) {
    filler->Fill(iter.fIndex);
    newMax = std::max(newMax, *t);
    iter++;
  }
  fMaxGlobalTimePerThread[tid].value.store(newMax);
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

  // In case of a multi-threaded simulation, extend the sorting time if needed,
  // depending on the GlobalTime difference between the slowest and fastest
  // progressing working thread.
  if (fNumWorkingThreads > 1) {
    auto [minIt, maxIt] = std::minmax_element(
        fMaxGlobalTimePerThread.get(),
        fMaxGlobalTimePerThread.get() + fNumWorkingThreads,
        [](const PaddedAtomicDouble &a, const PaddedAtomicDouble &b) {
          return a.value.load() < b.value.load();
        });
    const auto window =
        fMinimumSortingWindow + maxIt->value.load() - minIt->value.load();
    if (window > fSortingWindow) {
      fSortingWindow = window;
    }
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
      if (!fSortingWindowWarningIssued) {
        std::cout << "The digis in " << fInputCollection->GetName()
                  << " have non-monotonicities in the GlobalTime attribute "
                     "that exceed the sorting time ("
                  << fSortingWindow
                  << " ns). Please increase the sorting window to avoid "
                     "dropped digis\n";
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
          fSortingWindow)) {
    // Copy oldest digi into the output collection.
    fillerOut->Fill(fSortedIndicesA->top().index);
    // Keep track of the GlobalTime of the last digi that was copied.
    fMostRecentTimeDeparted = fSortedIndicesA->top().time;
    // Remove the time-sorted index of the digi.
    fSortedIndicesA->pop();
  }

  // The sorted digi collection keeps growing as more digis are processed.
  // The digis that have already been copied to the output must be removed
  // once in a while to limit memory usage. This is only done if at least 50% of
  // the occupied memory can be reclaimed.
  if (fSortedCollectionA->GetSize() > fMaxSize &&
      fSortedIndicesA->size() < fMaxSize / 2) {
    Prune();
  }

  // The current thread was the fastest one at the time when Process() got
  // called. Since it has been doing sorting work since, it may no longer be the
  // one with the highest GlobalTime value. So we have to re-evaluate which
  // thread is currently the fastest one.
  IdentifyFastestThread();
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
    std::cout << fNumDroppedDigi
              << " digis have been dropped while time-sorting. Please increase "
                 "the sorting time to a value higher than "
              << fMinimumSortingWindow << " ns\n";
  }
}

void GateTimeSorter::IdentifyFastestThread() {
  // Look up the index of the thread that currently has the largest GlobalTime
  // value.
  const auto maxIt = std::max_element(
      fMaxGlobalTimePerThread.get(),
      fMaxGlobalTimePerThread.get() + fNumWorkingThreads,
      [](const PaddedAtomicDouble &a, const PaddedAtomicDouble &b) {
        return a.value.load() < b.value.load();
      });
  fFastestThread.store(std::distance(fMaxGlobalTimePerThread.get(), maxIt));
}

void GateTimeSorter::MarkThreadAsFinished(int threadId) {
  // Sets the maximum observed GlobalTime of the given thread to zero, to make
  // sure that it can no longer be selected to do sorting work.
  fMaxGlobalTimePerThread[threadId].value.store(0.0);
  IdentifyFastestThread();
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
