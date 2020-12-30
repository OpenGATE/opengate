/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSourceMaster_h
#define GamSourceMaster_h

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"
#include "GamVSource.h"

class GamSourceManager : public G4VUserPrimaryGeneratorAction {
public:
    typedef std::pair<double, double> TimeInterval;
    typedef std::vector<TimeInterval> TimeIntervals;

    explicit GamSourceManager();

    // [py side] store the list of run time intervals
    void initialize(TimeIntervals simulation_times);

    // [py side] add a source to manage
    void add_source(GamVSource *source);

    // [py side] start the simulation, master thread only
    void start_main_thread();

    // Initialize a new Run
    void StartRun(int run_id);

    // Called by G4 engine
    void GeneratePrimaries(G4Event *anEvent) override;

    // After an event, prepare for the next
    void PrepareNextSource();

    // Check if the current run is terminated
    void CheckForNextRun();

    // Will be used by thread to initialize a new Run
    bool StartNewRun;
    int NextRunId;

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

};

#endif // GamSourceMaster_h
