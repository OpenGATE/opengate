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

    // Functions below --> use from python side

    explicit GamSourceMaster();

    void initialize(TimeIntervals simulation_times);

    void start();

    void add_source(GamVSource *source);

    // Functions below --> used only on cpp side

    void GeneratePrimaries(G4Event *anEvent) override;

    void PrepareNextSource();

    void StartRun(int run_id);

    void CheckForNextRun() const;

    TimeIntervals m_simulation_times;
    TimeInterval m_current_time_interval;
    double m_current_simulation_time;
    double m_next_simulation_time;
    GamVSource *m_next_active_source;
    std::vector<GamVSource *> m_sources;

};

#endif // GamSourceMaster_h
