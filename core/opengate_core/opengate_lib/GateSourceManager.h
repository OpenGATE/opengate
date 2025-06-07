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

#include "GateImageBox.h"
#include "GateUserEventInformation.h"
#include "GateVActor.h"
#include "GateVSource.h"
#include "indicators.hpp"

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

  // [available on py side] start the simulation master thread only
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

  void ComputeExpectedNumberOfEvents();

  static void SetRunTerminationFlag(bool flag);

  // fRunTerminationFlag should not be thread local
  static bool fRunTerminationFlag;
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

  bool fUserEventInformationFlag;
};

#endif // GateSourceManager_h
