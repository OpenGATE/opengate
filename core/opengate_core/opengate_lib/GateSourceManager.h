/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSourceManager_h
#define GateSourceManager_h

#include <G4Cache.hh>
#include <G4ParticleGun.hh>
#include <G4Threading.hh>
#include <G4UIExecutive.hh>
#include <G4UIsession.hh>
#include <G4VUserPrimaryGeneratorAction.hh>
#include <G4VisExecutive.hh>

#include "GateUserEventInformation.h"
#include "GateVActor.h"
#include "GateVSource.h"
#include "indicators.hpp"

using namespace indicators;

// Temporary: later option will be used to control the verbosity
class UIsessionSilent : public G4UIsession {
public:
  G4int ReceiveG4cout(const G4String & /*coutString*/) override { return 0; }

  G4int ReceiveG4cerr(const G4String & /*cerrString*/) override { return 0; }
};

/*
 * The source manager manages a set of sources.
 * There will be one copy per thread + one for the Master thread
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
  void Initialize(TimeIntervals simulation_times, py::dict &options);

  // [py side] add a source to manage
  void AddSource(GateVSource *source);

  // [py side] set the list of actors
  void SetActors(std::vector<GateVActor *> &actors);

  // Return a source
  GateVSource *FindSourceByName(std::string name) const;

  G4String GetActiveSourceName() {
    auto &l = fThreadLocalData.Get();
    if (l.fNextActiveSource != 0) {
      G4String name = l.fNextActiveSource->fName;
      return name;
    }
    return "None";
  }

  void SetActiveSourcebyName(G4String sourceName) {
    auto &l = fThreadLocalData.Get();
    auto *source = FindSourceByName(sourceName);
    l.fNextActiveSource = source;
  }

  // [available on py side] start the simulation, master thread only
  void StartMasterThread();

  // Initialize a new Run
  void PrepareRunToStart(int run_id);

  // Called by G4 fEngine
  void GeneratePrimaries(G4Event *anEvent) override;

  // After an event, prepare for the next
  void PrepareNextSource();

  // Check if the current run is terminated
  void CheckForNextRun();

  void InitializeVisualization();

  void InitializeProgressBar();

  bool IsEndOfSimulationForWorker() const;

  void StartVisualization() const;

  long int GetExpectedNumberOfEvents() const;

  void ComputeExpectedNumberOfEvents();

  void SetRunTerminationFlag(bool flag);

  // bool fRunTerminationFlag = false;
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

  // The following variables must be local to each threads
  struct threadLocalT {
    // Will be used by thread to initialize a new Run
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
    indicators::ProgressBar *fProgressBar{};
  };
  G4Cache<threadLocalT> fThreadLocalData;

  // List of managed sources
  std::vector<GateVSource *> fSources;

  // List of actors (for PreRunMaster callback)
  std::vector<GateVActor *> fActors;

  // List of run time intervals
  TimeIntervals fSimulationTimes;

  // static verbose level
  static int fVerboseLevel;

  // Options (visualisation for example)
  py::dict fOptions;

  bool fUserEventInformationFlag;
};

#endif // GateSourceManager_h
