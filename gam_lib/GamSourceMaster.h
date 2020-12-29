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

class GamSourceMaster : public G4VUserPrimaryGeneratorAction {
public:
    typedef std::pair<double, double> TimeInterval;
    typedef std::vector<TimeInterval> TimeIntervals;

    explicit GamSourceMaster();

    // [py side] store the list of run time intervals
    void initialize(TimeIntervals simulation_times);

    // [py side] add a source to manage
    void add_source(GamVSource *source);

    // [py side] start the simulation, master thread only
    void start();

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
    TimeIntervals m_simulation_times;

    // Current time interval (start/stop)
    TimeInterval m_current_time_interval;

    // Current simulation time
    double m_current_simulation_time;

    // Next simulation time
    double m_next_simulation_time;

    // Next active source
    GamVSource *m_next_active_source;

    // List of managed sources
    std::vector<GamVSource *> m_sources;

};

#endif // GamSourceMaster_h
