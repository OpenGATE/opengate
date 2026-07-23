/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSourceManager_h
#define GateSourceManager_h

#include "GateImageBox.h"
#include "GateUserEventInformation.h"
#include "GateVActor.h"
#include "GateVSource.h"
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4244 4267)
#endif
#include "indicators.hpp"
#if defined(_MSC_VER)
#pragma warning(pop)
#endif
#include <G4Cache.hh>
#include <G4ParticleGun.hh>
#include <G4Threading.hh>
#include <G4UIExecutive.hh>
#include <G4UIsession.hh>
#include <G4VUserPrimaryGeneratorAction.hh>
#include <G4VisExecutive.hh>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <mutex>
#include <pybind11/pybind11.h>

namespace py = pybind11;

using namespace indicators;

// Temporary: later options will be used to control the verbosity
class UIsessionSilent : public G4UIsession {
public:
  G4int ReceiveG4cout(const G4String & /*coutString*/) override { return 0; }

  G4int ReceiveG4cerr(const G4String & /*cerrString*/) override { return 0; }
};

/*
 * The source manager manages a set of sources.
 * There will be one copy per thread plus one for the Master thread
 * Only the master thread call StartMasterThread
 *
 * The Geant4 fEngine will call GeneratePrimaries for all threads
 *
 * GeneratePrimaries:
 * - select one source according to the time
 * - check end of run
 *
 */

class GateSourceManager : public G4VUserPrimaryGeneratorAction {
public:
  typedef std::pair<double, double> TimeInterval;
  typedef std::vector<TimeInterval> TimeIntervals;

  explicit GateSourceManager();

  ~GateSourceManager() override;

  // [py side] store the list of run time intervals
  void Initialize(const TimeIntervals &simulation_times, py::dict &options);

  // [py side] add a source to manage
  void AddSource(GateVSource *source);

  // [py side] set the list of actors
  void SetActors(const std::vector<GateVActor *> &actors);

  // Return a source
  GateVSource *FindSourceByName(const std::string &name) const;

  // Return the name of the active source
  G4String GetActiveSourceName();

  // Set the active source by name
  void SetActiveSourcebyName(G4String sourceName);

  // [available on py side] start the simulation, master thread only
  void StartMasterThread();

  // Initialise a new Run
  void PrepareRunToStart(int run_id);

  // Called by G4 fEngine
  void GeneratePrimaries(G4Event *event) override;

  // After an event, prepare for the next
  void PrepareNextSource() const;

  // Check if the current run is terminated
  void CheckForNextRun() const;

  void InitializeVisualization();

  void InitializeProgressBar();

  void RegisterImageBox(GateImageBox *g4Solid);

  bool IsEndOfSimulationForWorker() const;

  void StartVisualization() const;

  long int GetExpectedNumberOfEvents() const;

  unsigned long GetRunGeneratedEvents() const;
  unsigned long GetTotalGeneratedEvents() const;

  double GetCurrentSimulationTime() const;
  int GetCurrentRunId() const;

  void ComputeExpectedNumberOfEvents();

  void SetProgressReportCallback(py::function func, double interval_seconds);

  void CheckProgressReport() const;

  static void SetRunTerminationFlag(bool flag);
  static void ResetPrimaryCounterForRun();
  static bool TryReservePrimarySlot();
  static void WarnPrimaryLimitReached();
  static void SetMaxPrimariesPerRun(std::uint64_t value);
  static std::uint64_t GetPlatformMaxPrimariesPerRun();

  // fRunTerminationFlag should not be thread local
  static bool fRunTerminationFlag;
  static std::atomic<std::uint64_t> fGeneratedPrimariesThisRun;
  static std::atomic<bool> fPrimaryLimitWarningIssued;
  static std::uint64_t fMaxPrimariesPerRun;
  bool fVisualizationFlag;
  bool fVisualizationVerboseFlag;
  std::string fVisualizationType;
  std::string fVisualizationFile;
  G4UIExecutive *fUIEx;
  std::vector<std::string> fVisCommands;
  UIsessionSilent fSilent;

  bool fProgressBarFlag;
  long int fExpectedNumberOfEvents;
  long int fProgressBarStep;
  long int fCurrentEvent;

  // The following variables must be local to each thread
  struct threadLocalT {
    // Will be used by thread to initialise a new Run
    bool fStartNewRun;
    int fNextRunId;

    // Current simulation time
    double fCurrentSimulationTime;

    // Current time interval (start/stop)
    TimeInterval fCurrentTimeInterval;

    // Next simulation time
    double fNextSimulationTime;

    // Next active source
    GateVSource *fNextActiveSource;

    // User information data
    GateUserEventInformation *fUserEventInformation;

    // progress bar
    // indicators::ProgressBar *fProgressBar;
    std::unique_ptr<indicators::ProgressBar> fProgressBar;
  };
  G4Cache<threadLocalT> fThreadLocalData;

  // List of managed sources
  std::vector<GateVSource *> fSources;

  // List of GateImageBox
  std::vector<GateImageBox *> fImageBoxes;

  // List of actors (for PreRunMaster callback)
  std::vector<GateVActor *> fActors;

  // List of run time intervals
  TimeIntervals fSimulationTimes;

  // verbose level
  int fVerboseLevel;

  // Options (visualisation for example)
  py::dict fOptions;

  // Progress report
  double fProgressReportInterval;
  py::function fProgressReportCallback;
  mutable std::chrono::steady_clock::time_point
      fLastProgressReportTime; // (mutable needed in CheckProgressReport)
  mutable std::mutex
      fProgressReportMutex; // (mutable needed in CheckProgressReport)

  bool fUserEventInformationFlag;
};

#endif // GateSourceManager_h
