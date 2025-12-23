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

  void Init(const std::string &name, GateDigiCollection *input,
            GateDigiCollection *output);

  void SetDelay(double delay);
  void SetMaxSize(size_t size);

  void Process();
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
    GateDigiCollection *digis;
    std::priority_queue<TimedDigiIndex, std::vector<TimedDigiIndex>,
                        std::greater<TimedDigiIndex>>
        sortedIndices;
    std::unique_ptr<GateDigiAttributesFiller> fillerIn;
    std::unique_ptr<GateDigiAttributesFiller> fillerOut;
    std::unique_ptr<GateDigiAttributesFiller> fillerSwap;
  };

  GateDigiCollectionIterator fInputIter;
  double *fTime;
  double fDelay{1000.0}; // nanoseconds
  size_t fMaxSize{100'000};
  bool fInitialized{false};
  bool fProcessingStarted{false};
  bool fFlushed{false};
  std::optional<double> fMostRecentTimeArrived;
  std::optional<double> fMostRecentTimeDeparted;
  std::unique_ptr<TimeSortedStorage> fCurrentStorage;
  std::unique_ptr<TimeSortedStorage> fFutureStorage;
};

#endif // GateTimeSorter_h
