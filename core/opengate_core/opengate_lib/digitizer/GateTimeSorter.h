#ifndef GateTimeSorter_h
#define GateTimeSorter_h

#include "GateDigiCollectionIterator.h"
#include <memory>
#include <optional>
#include <queue>

class GateDigiCollection;
class GateDigiAttributesFiller;

class GateTimeSorter {
public:
  GateTimeSorter() = default;

  void Init(GateDigiCollection *input);

  void SetSortingWindow(double duration);
  void SetMaxSize(size_t size);

  std::unique_ptr<GateDigiAttributesFiller>
  CreateFiller(GateDigiCollection *destination);
  GateDigiCollection::Iterator &OutputIterator();
  void Process();
  void MarkOutputAsProcessed();
  void Flush();

private:
  void Prune();

  struct TimedDigiIndex {
    size_t index;
    double time;

    bool operator>(const TimedDigiIndex &other) const {
      return time > other.time;
    }
  };

  struct TimeSortedStorage {
    TimeSortedStorage(GateDigiCollection *input, GateDigiCollection *output,
                      const std::string &name_suffix);

    GateDigiCollection *digis;
    std::priority_queue<TimedDigiIndex, std::vector<TimedDigiIndex>,
                        std::greater<TimedDigiIndex>>
        sortedIndices;
    std::unique_ptr<GateDigiAttributesFiller> fillerIn;
    std::unique_ptr<GateDigiAttributesFiller> fillerOut;
  };

  double fSortingWindow{1000.0}; // nanoseconds
  size_t fMaxSize{100'000};

  GateDigiCollection *fInputCollection;
  GateDigiCollectionIterator fInputIter;

  GateDigiCollection *fOutputCollection;
  GateDigiCollectionIterator fOutputIter;

  double *fTime;

  bool fInitialized{false};
  bool fProcessingStarted{false};
  bool fFlushed{false};
  bool fSortingWindowWarningIssued{false};
  std::optional<double> fMostRecentTimeArrived;
  std::optional<double> fMostRecentTimeDeparted;

  std::unique_ptr<TimeSortedStorage> fCurrentStorage;
  std::unique_ptr<TimeSortedStorage> fFutureStorage;
};

#endif // GateTimeSorter_h
