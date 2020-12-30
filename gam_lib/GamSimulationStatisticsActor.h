/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSimulationStatisticsActor_h
#define GamSimulationStatisticsActor_h

#include "G4Accumulable.hh"
#include "GamVActor.h"

class GamSimulationStatisticsActor : public GamVActor {

public:

    explicit GamSimulationStatisticsActor(std::string type_name);

    virtual ~GamSimulationStatisticsActor();

    // Called when the simulation start (master thread only)
    virtual void StartSimulationAction();

    // Called when the simulation end (master thread only)
    virtual void EndSimulationAction();

    // Called every time a Run starts (all threads)
    virtual void BeginOfRunAction(const G4Run *run);

    // Called every time a Run ends (all threads)
    virtual void EndOfRunAction(const G4Run *run);

    // Called every time an Event starts (all threads)
    //virtual void BeginOfEventAction(const G4Event *event);

    // Called every time a Track starts (all threads)
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingAction(G4Step *, G4TouchableHistory *);

    int run_count() { return fRunCount.GetValue(); }

    int event_count() { return fEventCount.GetValue(); }

    int track_count() { return fTrackCount.GetValue(); }

    int step_count() { return fStepCount.GetValue(); }

    void set_run_count(int i) { fRunCount = i; }

    void set_event_count(int i) { fEventCount = i; }

    void set_track_count(int i) { fTrackCount = i; }

    void set_step_count(int i) { fStepCount = i; }

    G4Accumulable<int> fRunCount;
    G4Accumulable<int> fEventCount;
    G4Accumulable<int> fTrackCount;
    G4Accumulable<int> fStepCount;

    double duration;
    std::chrono::steady_clock::time_point fStartTime;
    std::chrono::steady_clock::time_point fStopTime;
};

#endif // GamSimulationStatisticsActor_h
