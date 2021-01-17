/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSourceManager_h
#define GamSourceManager_h

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"
#include "G4UIExecutive.hh"
#include "G4VisExecutive.hh"
#include "GamVSource.h"

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

    // [py side] start the simulation, master thread only
    void StartMainThread();

    // Initialize a new Run
    void PrepareRunToStart(int run_id);

    // Called by G4 engine
    void GeneratePrimaries(G4Event *anEvent) override;

    // After an event, prepare for the next
    void PrepareNextSource();

    // Check if the current run is terminated
    void CheckForNextRun();

    void InitializeVisualization();

    void StartVisualization();

    bool fVisualizationFlag;
    G4UIExecutive *fUIEx;
    G4VisExecutive *fVisEx;

    // Will be used by thread to initialize a new Run
    bool fStartNewRun;
    size_t fNextRunId;

    // List of run time intervals
    TimeIntervals fSimulationTimes;

    // Current time interval (start/stop)
    TimeInterval fCurrentTimeInterval;

    // Current simulation time
    double fCurrentSimulationTime;

    // Next simulation time
    double fNextSimulationTime;

    // Next active source
    GamVSource *fNextActiveSource;

    // List of managed sources
    std::vector<GamVSource *> fSources;

    // Options (visualisation for example)
    py::dict fOptions;
};

#endif // GamSourceManager_h
