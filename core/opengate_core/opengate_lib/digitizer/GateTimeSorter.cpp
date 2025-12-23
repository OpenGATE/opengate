#include "GateTimeSorter.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <memory>

void GateTimeSorter::Init(GateDigiCollection *input) {
  fInputCollection = input;
  fInputIter = fInputCollection->NewIterator();
  fInputIter.TrackAttribute("GlobalTime", &fTime);

  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto attribute_names = fInputCollection->GetDigiAttributeNames();

  fOutputCollection =
      manager->NewDigiCollection(fInputCollection->GetName() + "_sorted");
  fOutputCollection->InitDigiAttributesFromCopy(fInputCollection);
  fOutputIter = fOutputCollection->NewIterator();

  fCurrentStorage = std::make_unique<TimeSortedStorage>();
  fCurrentStorage->digis =
      manager->NewDigiCollection(fInputCollection->GetName() + "_temporaryA");
  fCurrentStorage->digis->InitDigiAttributesFromCopy(fInputCollection);
  fCurrentStorage->fillerIn = std::make_unique<GateDigiAttributesFiller>(
      fInputCollection, fCurrentStorage->digis, attribute_names);
  fCurrentStorage->fillerOut = std::make_unique<GateDigiAttributesFiller>(
      fCurrentStorage->digis, fOutputCollection, attribute_names);

  fFutureStorage = std::make_unique<TimeSortedStorage>();
  fFutureStorage->digis =
      manager->NewDigiCollection(fInputCollection->GetName() + "_temporaryB");
  fFutureStorage->digis->InitDigiAttributesFromCopy(fInputCollection);
  fFutureStorage->fillerIn = std::make_unique<GateDigiAttributesFiller>(
      fInputCollection, fFutureStorage->digis, attribute_names);
  fFutureStorage->fillerOut = std::make_unique<GateDigiAttributesFiller>(
      fFutureStorage->digis, fOutputCollection, attribute_names);

  fInitialized = true;
}

void GateTimeSorter::SetSortingWindow(double duration) {
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
  if (!fInitialized) {
    Fatal("CreateFiller() called before Init().");
  }
  return std::make_unique<GateDigiAttributesFiller>(
      fOutputCollection, destination,
      fOutputCollection->GetDigiAttributeNames());
}

GateDigiCollection::Iterator &GateTimeSorter::OutputIterator() {
  return fOutputIter;
}

void GateTimeSorter::Process() {
  if (fFlushed) {
    Fatal("Process called after Flush(). The time sorter must not be used "
          "after it was flushed.");
  }
  fProcessingStarted = true;

  auto &iter = fInputIter;
  auto &sortedIndices = fCurrentStorage->sortedIndices;

  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    const size_t digiIndex = fCurrentStorage->digis->GetSize();
    const double digiTime = *fTime;
    if (fMostRecentTimeDeparted.has_value() &&
        (digiTime < *fMostRecentTimeDeparted)) {
      // TODO warn that digi was dropped to be able to guarantee time
      // monotonicity and that delay parameter should be increased.
    } else {
      fCurrentStorage->fillerIn->Fill(iter.fIndex);
      sortedIndices.push({digiIndex, digiTime});

      if (!fMostRecentTimeArrived || (digiTime > *fMostRecentTimeArrived)) {
        fMostRecentTimeArrived = digiTime;
      }
    }
    iter++;
  }

  if (!sortedIndices.empty()) {
    size_t num_filled = 0;
    double timespan = *fMostRecentTimeArrived - sortedIndices.top().time;
    while (!sortedIndices.empty() && timespan > fSortingWindow) {
      fCurrentStorage->fillerOut->Fill(sortedIndices.top().index);
      fMostRecentTimeDeparted = sortedIndices.top().time;
      sortedIndices.pop();
      if (!sortedIndices.empty()) {
        timespan = *fMostRecentTimeArrived - sortedIndices.top().time;
      }
      num_filled++;
    }
  }

  if (fCurrentStorage->digis->GetSize() > fMaxSize) {
    Prune();
  }
}

void GateTimeSorter::MarkOutputAsProcessed() {
  if (fOutputCollection->GetSize() <= fMaxSize) {
    fOutputCollection->SetBeginOfEventIndex(fOutputIter.fIndex);
  } else {
    fOutputCollection->Clear();
    fOutputIter.Reset();
  }
}

void GateTimeSorter::Flush() {
  auto &sortedIndices = fCurrentStorage->sortedIndices;
  while (sortedIndices.size() > 0) {
    fCurrentStorage->fillerOut->Fill(sortedIndices.top().index);
    sortedIndices.pop();
  }
  Prune();
  fFlushed = true;
}

void GateTimeSorter::Prune() {
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
