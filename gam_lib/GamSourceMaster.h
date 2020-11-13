/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSourceMaster_h
#define GamSourceMaster_h

#include "GamVSource.h"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleGun.hh"

class GamSourceMaster : public G4VUserPrimaryGeneratorAction {
public:
    typedef std::pair<double, double> TimeInterval;
    typedef std::vector<TimeInterval> TimeIntervals;

    void initialize(TimeIntervals simulation_times);

    void start();

    void add_source(GamVSource *source);

    void GeneratePrimaries(G4Event *anEvent) override;

    void PrepareNextSource();

    void StartRun(int run_id);

    void CheckForNextRun();

    TimeIntervals m_simulation_times;
    TimeInterval m_current_time_interval;
    double m_current_simulation_time;
    double m_next_simulation_time;
    GamVSource *m_next_active_source;
    std::vector<GamVSource *> m_sources;

    // debug
    int nb = 0;
    G4ParticleGun *m_particle_gun;

};

#endif // GamSourceMaster_h
