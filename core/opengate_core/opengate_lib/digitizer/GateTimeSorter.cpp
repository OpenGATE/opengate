#include "GateTimeSorter.h"
#include "GateDigiCollection.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <memory>

void GateTimeSorter::Init(const std::string &name, GateDigiCollection *input,
                          GateDigiCollection *output) {
  if (fInitialized) {
    Fatal("Init() cannot be called more than once.");
  }

  fInputIter = input->NewIterator();
  fInputIter.TrackAttribute("GlobalTime", &fTime);

  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto attribute_names = input->GetDigiAttributeNames();

  fCurrentStorage = std::make_unique<TimeSortedStorage>();
  fCurrentStorage->digis = manager->NewDigiCollection(name + "_collectionA");
  fCurrentStorage->digis->InitDigiAttributesFromCopy(input);
  fCurrentStorage->fillerIn = std::make_unique<GateDigiAttributesFiller>(
      input, fCurrentStorage->digis, attribute_names);
  fCurrentStorage->fillerOut = std::make_unique<GateDigiAttributesFiller>(
      fCurrentStorage->digis, output, attribute_names);

  fFutureStorage = std::make_unique<TimeSortedStorage>();
  fFutureStorage->digis = manager->NewDigiCollection(name + "_collectionB");
  fFutureStorage->digis->InitDigiAttributesFromCopy(input);
  fFutureStorage->fillerIn = std::make_unique<GateDigiAttributesFiller>(
      input, fFutureStorage->digis, attribute_names);
  fFutureStorage->fillerOut = std::make_unique<GateDigiAttributesFiller>(
      fFutureStorage->digis, output, attribute_names);

  fCurrentStorage->fillerSwap = std::make_unique<GateDigiAttributesFiller>(
      fCurrentStorage->digis, fFutureStorage->digis, attribute_names);
  fFutureStorage->fillerSwap = std::make_unique<GateDigiAttributesFiller>(
      fFutureStorage->digis, fCurrentStorage->digis, attribute_names);

  fInitialized = true;
}

void GateTimeSorter::SetDelay(double delay) {
  if (fProcessingStarted) {
    Fatal("SetDelay() cannot be called after Process() has been called.");
  }
  fDelay = delay;
}

void GateTimeSorter::SetMaxSize(size_t maxSize) {
  if (fProcessingStarted) {
    Fatal("SetMaxSize() cannot be called after Process() has been called.");
  }
  fMaxSize = maxSize;
}

void GateTimeSorter::Process() {
  if (!fInitialized) {
    Fatal("Process() called before Init(). "
          "Init() must be called first to initialize the time sorter.");
  }
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
    while (!sortedIndices.empty() && timespan > fDelay) {
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
