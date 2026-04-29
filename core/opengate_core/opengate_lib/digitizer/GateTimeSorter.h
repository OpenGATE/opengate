#ifndef GateTimeSorter_h
#define GateTimeSorter_h

#include "GateDigiCollectionIterator.h"
#include <G4Threading.hh>
#include <atomic>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <queue>

class GateDigiCollection;
class GateDigiAttributesFiller;

class GateTimeSorter {
public:
  GateTimeSorter();

  void Init(GateDigiCollection *input);

  void SetSortingWindow(double duration);
  void SetMaxSize(size_t size);

  GateDigiCollection *OutputCollection() const;
  std::unique_ptr<GateDigiAttributesFiller>
  CreateFiller(GateDigiCollection *destination);
  GateDigiCollection::Iterator &OutputIterator();
  void Ingest();
  void Process();
  void MarkOutputAsProcessed();
  void MarkThreadAsFinished(int threadId);
  void IdentifyFastestThread();
  void Flush();

  void OnEndOfEventAction(std::function<void(void)> work);
  void OnEndOfRunAction(std::function<void(void)> anyThreadWork,
                        std::function<void(void)> lastThreadWork);

private:
  void Prune();

  struct TimedDigiIndex {
    size_t index;
    double time;

    bool operator>(const TimedDigiIndex &other) const {
      return time > other.time;
    }
  };

  typedef std::priority_queue<TimedDigiIndex, std::vector<TimedDigiIndex>,
                              std::greater<TimedDigiIndex>>
      TimeSortedIndices;

  double fMinimumSortingWindow{1000.0}; // nanoseconds
  double fSortingWindow{1000.0};        // nanoseconds
  size_t fMaxSize{100'000};

  // Pad atomic<double> to one cache line (64 bytes) to prevent false sharing
  // when N threads each write to their own element in a tight loop.
  struct alignas(64) PaddedAtomicDouble {
    std::atomic<double> value{0.0};
  };

  std::unique_ptr<PaddedAtomicDouble[]> fMaxGlobalTimePerThread;
  std::atomic<int> fFastestThread{};
  std::atomic<int> fNumActiveWorkingThreads{};
  std::atomic<bool> fProcessing{};
  std::atomic<int> fNumIngestions{};

  int fNumThreads{0};
  G4Mutex fMutex;

  GateDigiCollection *fInputCollection;

  GateDigiCollection *fBufferA;
  GateDigiCollection *fBufferB;

  GateDigiCollection *fSortedCollectionA;
  std::unique_ptr<TimeSortedIndices> fSortedIndicesA;
  GateDigiCollection *fSortedCollectionB;
  std::unique_ptr<TimeSortedIndices> fSortedIndicesB;

  GateDigiCollection *fOutputCollection;
  GateDigiCollectionIterator fOutputIter;

  std::map<std::pair<GateDigiCollection *, GateDigiCollection *>,
           std::unique_ptr<GateDigiAttributesFiller>>
      fFillers;

  bool fInitialized{false};
  bool fProcessingStarted{false};
  bool fFlushed{false};
  bool fSortingWindowWarningIssued{false};
  size_t fNumDroppedDigi{};
  std::optional<double> fMostRecentTimeArrived;
  std::optional<double> fMostRecentTimeDeparted;
};

#endif // GateTimeSorter_h
