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

  void OnEndOfEventAction(std::function<void(void)> work);
  void OnEndOfRunAction(std::function<void(void)> anyThreadWork,
                        std::function<void(void)> lastThreadWork);

  GateDigiCollection *OutputCollection() const;
  GateDigiCollection::Iterator &OutputIterator();
  void MarkOutputAsProcessed();

  void Ingest();
  void Process();
  void Flush();

private:
  void IdentifyFastestThread();
  void MarkThreadAsFinished(int threadId);
  void Prune();

  double fMinimumSortingWindow{1000.0}; // nanoseconds
  double fSortingWindow{1000.0};        // nanoseconds
  size_t fMaxSize{100'000};             // digis

  // Threading

  G4Mutex fIngestionMutex;
  int fNumWorkingThreads{};
  std::atomic<int> fFastestThread{};
  std::atomic<int> fNumActiveWorkingThreads{};
  std::atomic<bool> fProcessingOngoing{};
  std::atomic<int> fNumIngestions{};

  struct alignas(64) PaddedAtomicDouble {
    // Pad atomic<double> to one cache line (64 bytes) to prevent false sharing
    // when N threads each write to their own element in a tight loop.
    std::atomic<double> value{};
  };
  std::unique_ptr<PaddedAtomicDouble[]> fMaxGlobalTimePerThread;

  // Digi storage, sorting and copying

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

  GateDigiCollection *fInputCollection;

  GateDigiCollection *fIngestionBufferA;
  GateDigiCollection *fIngestionBufferB;

  GateDigiCollection *fSortedCollectionA;
  std::unique_ptr<TimeSortedIndices> fSortedIndicesA;
  GateDigiCollection *fSortedCollectionB;
  std::unique_ptr<TimeSortedIndices> fSortedIndicesB;

  GateDigiCollection *fOutputCollection;
  GateDigiCollectionIterator fOutputIter;

  std::map<std::pair<GateDigiCollection *, GateDigiCollection *>,
           std::unique_ptr<GateDigiAttributesFiller>>
      fFillers;

  // GateTimeSorter internal state

  bool fInitialized{false};
  bool fProcessingStarted{false};
  bool fFlushed{false};
  bool fSortingWindowWarningIssued{false};
  size_t fNumDroppedDigi{};
  std::optional<double> fMostRecentTimeArrived;
  std::optional<double> fMostRecentTimeDeparted;
};

#endif // GateTimeSorter_h
