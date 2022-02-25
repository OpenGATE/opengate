/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSourceManager_h
#define GamSourceManager_h

#include <G4VUserPrimaryGeneratorAction.hh>
#include <G4ParticleGun.hh>
#include <G4UIExecutive.hh>
#include <G4VisExecutive.hh>
#include <G4UIsession.hh>
#include <G4Threading.hh>
#include <G4Cache.hh>
#include "GamVSource.h"

// Temporary: later option will be used to control the verbosity
class UIsessionSilent : public G4UIsession {
public:

    virtual G4int ReceiveG4cout(const G4String & /*coutString*/) { return 0; }

    virtual G4int ReceiveG4cerr(const G4String & /*cerrString*/) { return 0; }
};

/*
 * The source manager manages a set of sources.
 * There will be one copy per thread + one for the Master thread
 * Only the master thread call StartMasterThread
 *
 * The Geant4 engine will call GeneratePrimaries for all threads
 *
 * GeneratePrimaries:
 * - select one source according to the time
 * - check end of run
 *
 */

class GamSourceManager : public G4VUserPrimaryGeneratorAction {
public:
    typedef std::pair<double, double> TimeInterval;
    typedef std::vector<TimeInterval> TimeIntervals;

    explicit GamSourceManager();

    virtual ~GamSourceManager();

    // [py side] store the list of run time intervals
    void Initialize(TimeIntervals simulation_times, py::dict &options);

    // [py side] add a source to manage
    void AddSource(GamVSource *source);

    // [available on py side] start the simulation, master thread only
    void StartMasterThread();

    // Initialize a new Run
    void PrepareRunToStart(int run_id);

    // Called by G4 engine
    void GeneratePrimaries(G4Event *anEvent) override;

    // After an event, prepare for the next
    void PrepareNextSource();

    // Check if the current run is terminated
    void CheckForNextRun();

    void InitializeVisualization();

    bool IsEndOfSimulationForWorker() const;

    void StartVisualization() const;

    bool fVisualizationFlag;
    bool fVisualizationVerboseFlag;
    G4UIExecutive *fUIEx;
    G4VisExecutive *fVisEx;
    std::vector<std::string> fVisCommands;
    UIsessionSilent fSilent;

    // Will be used by thread to initialize a new Run
    bool fStartNewRun;
    size_t fNextRunId;

    // Current simulation time
    double fCurrentSimulationTime;

    // Current time interval (start/stop)
    TimeInterval fCurrentTimeInterval;

    // Next simulation time
    double fNextSimulationTime;

    // Next active source
    GamVSource *fNextActiveSource;

    // List of managed sources
    std::vector<GamVSource *> fSources;

    // List of run time intervals
    TimeIntervals fSimulationTimes;

    // static verbose level
    static int fVerboseLevel;

    // Options (visualisation for example)
    py::dict fOptions;
};

#endif // GamSourceManager_h
