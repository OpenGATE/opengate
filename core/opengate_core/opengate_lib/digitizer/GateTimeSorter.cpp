#include "GateTimeSorter.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <memory>

GateTimeSorter::TimeSortedStorage::TimeSortedStorage(
    GateDigiCollection *input, GateDigiCollection *output,
    const std::string &name_suffix) {

  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto attribute_names = input->GetDigiAttributeNames();

  // GateDigiCollection for temporary storage
  digis = manager->NewDigiCollection(input->GetName() + "_" + name_suffix);
  digis->InitDigiAttributesFromCopy(input);

  // Filler to copy from input collection to temporary collection
  fillerIn =
      std::make_unique<GateDigiAttributesFiller>(input, digis, attribute_names);

  // Filler to copy from temporary to output collection
  fillerOut = std::make_unique<GateDigiAttributesFiller>(digis, output,
                                                         attribute_names);

  // The GateDigiCollection contains the digis in the order in which they were
  // added using fillerIn, but the actual sorting happens in the priority queue
  // sortedIndices.
}

void GateTimeSorter::Init(GateDigiCollection *input) {

  // Create an iterator for the input collection, tracking the GlobalTime of
  // digis to be able to sort them in time.
  fInputCollection = input;
  fInputIter = fInputCollection->NewIterator();
  fInputIter.TrackAttribute("GlobalTime", &fTime);

  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto attribute_names = fInputCollection->GetDigiAttributeNames();

  // Create an output collection that will receive the time-sorted digis, and an
  // iterator for the output collection.
  fOutputCollection =
      manager->NewDigiCollection(fInputCollection->GetName() + "_sorted");
  fOutputCollection->InitDigiAttributesFromCopy(fInputCollection);
  fOutputIter = fOutputCollection->NewIterator();

  // Create a TimeSortedStorage object for sorting digis.
  fCurrentStorage = std::make_unique<TimeSortedStorage>(
      fInputCollection, fOutputCollection, "temporaryA");

  // Create a second TimeSortedStorage object that will be used later, when the
  // first one's memory needs to be freed.
  fFutureStorage = std::make_unique<TimeSortedStorage>(
      fInputCollection, fOutputCollection, "temporaryB");

  fInitialized = true;
}

void GateTimeSorter::SetSortingWindow(double duration) {
  // The sorting window, specified in nanoseconds, is the difference in
  // GlobalTime between the oldest and newest digi being stored in the
  // TimeSortedStorage object, before they are transferred to the output
  // collection. Since the GlobalTime of incoming digis is not guaranteed to
  // increase monotonically, the sorting window must be large enough to ensure
  // that all digis can be properly time-sorted.
  // Non-monotonicity of GlobalTime can be caused by the time difference between
  // a particle's generation and its interaction with a detector. It can also be
  // caused by a DigitizerBlurringActor with blur_attribute "GlobalTime".

  if (fProcessingStarted) {
    Fatal("SetDelay() cannot be called after Process() has been called.");
  }
  fSortingWindow = duration;
}

void GateTimeSorter::SetMaxSize(size_t maxSize) {
  if (fProcessingStarted) {
    Fatal("SetMaxSize() cannot be called after Process() has been called.");
  }
  fMaxSize = maxSize;
}

std::unique_ptr<GateDigiAttributesFiller>
GateTimeSorter::CreateFiller(GateDigiCollection *destination) {
  // Creates a GateDigiAttributesFiller from the TimeSorter's output collection
  // into the given destination GateDigiCollection.

  if (!fInitialized) {
    Fatal("CreateFiller() called before Init().");
  }
  return std::make_unique<GateDigiAttributesFiller>(
      fOutputCollection, destination,
      fOutputCollection->GetDigiAttributeNames());
}

GateDigiCollection::Iterator &GateTimeSorter::OutputIterator() {
  // Provides access to the GateTimeSorter's output iterator.
  return fOutputIter;
}

void GateTimeSorter::Process() {
  // Processes all digis from the input collection by copying and sorting them
  // according to GlobalTime. Next, copies the oldest sorted digis to the output
  // collection.

  if (fFlushed) {
    Fatal("Process called after Flush(). The time sorter must not be used "
          "after it was flushed.");
  }
  fProcessingStarted = true;

  auto &iter = fInputIter;
  auto &sortedIndices = fCurrentStorage->sortedIndices;

  // Iterate over the input collection and sort the digis.
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    const size_t digiIndex = fCurrentStorage->digis->GetSize();
    const double digiTime = *fTime;
    if (fMostRecentTimeDeparted.has_value() &&
        (digiTime < *fMostRecentTimeDeparted)) {
      // The digi is dropped, in order to be able to guarantee monotonous
      // GlobalTime in the output collection.
      if (!fSortingWindowWarningIssued) {
        std::cout << "The digis in " << fInputCollection->GetName()
                  << " have non-monotonicities in the GlobalTime attribute "
                     "that exceed "
                     "the sorting window ("
                  << fSortingWindow
                  << " ns). Please increase the sorting window to avoid "
                     "dropped digis";
        fSortingWindowWarningIssued = true;
      }
    } else {
      // Copy the digi into the temporary digi collection.
      fCurrentStorage->fillerIn->Fill(iter.fIndex);
      // Keep a time-sorted list of indices into the temporary digi collection.
      sortedIndices.push({digiIndex, digiTime});

      // Keep track of the highest GlobalTime observed so far.
      if (!fMostRecentTimeArrived || (digiTime > *fMostRecentTimeArrived)) {
        fMostRecentTimeArrived = digiTime;
      }
    }
    iter++;
  }

  // Copy the oldest digis from the sorted temporary storage into the output
  // collection. Continue as long as the newest digi is at least fSortingWindow
  // more recent than the oldest digi.
  while (
      !sortedIndices.empty() &&
      (*fMostRecentTimeArrived - sortedIndices.top().time > fSortingWindow)) {
    // Copy oldest digi into the output collection.
    fCurrentStorage->fillerOut->Fill(sortedIndices.top().index);
    // Keep track of the GlobalTime of the last digi that was copied.
    fMostRecentTimeDeparted = sortedIndices.top().time;
    // Remove the time-sorted index of the digi.
    sortedIndices.pop();
  }

  // The temporary digi collection keeps growing as more digis are processed.
  // The digis that have already been copied to the output must be removed once
  // in a while to limit memory usage.
  if (fCurrentStorage->digis->GetSize() > fMaxSize) {
    Prune();
  }
}

void GateTimeSorter::MarkOutputAsProcessed() {
  // Modifies the start of event index, to ensure that future use of the
  // iterator starts with the output digis that have not been processed yet.
  // Once in a while, the output collection is cleared to reduce memory
  // consumption.
  if (fOutputCollection->GetSize() <= fMaxSize) {
    fOutputCollection->SetBeginOfEventIndex(fOutputIter.fIndex);
  } else {
    fOutputCollection->Clear();
    fOutputIter.Reset();
  }
}

void GateTimeSorter::Flush() {
  // Copies all remaining sorted digis into the output collection.
  // This method is intended to be called once at the end of time sorting, when
  // it is known that no more digis will be processed from the input.
  // As a consequence, the sorting window does not have to be taken into account
  // while flushing.
  auto &sortedIndices = fCurrentStorage->sortedIndices;
  while (sortedIndices.size() > 0) {
    fCurrentStorage->fillerOut->Fill(sortedIndices.top().index);
    sortedIndices.pop();
  }
  Prune();
  fFlushed = true;
}

void GateTimeSorter::Prune() {
  // Frees memory that is currently occupied by digis that have already been
  // copied into the output collection:
  // 1. The digis that have not been copied to the output yet, are copied into
  // the second instance of TimeSortedStorage.
  // 2. The digi collection in the first instance of TimeSortedStorage is
  // cleared.
  // 3. The two instances of TimeSortedStorage are swapped.

  auto &sortedIndices = fCurrentStorage->sortedIndices;
  while (!sortedIndices.empty()) {
    const auto timed_index = sortedIndices.top();
    sortedIndices.pop();
    const size_t digiIndex = fFutureStorage->digis->GetSize();
    const double digiTime = timed_index.time;
    fCurrentStorage->fillerSwap->Fill(timed_index.index);
    fFutureStorage->sortedIndices.push({digiIndex, digiTime});
  }
  fCurrentStorage->digis->Clear();
  std::swap(fCurrentStorage, fFutureStorage);
}
