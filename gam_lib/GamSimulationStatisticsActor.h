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
//#include "G4GenericAnalysisManager.hh"
//using G4AnalysisManager = G4GenericAnalysisManager;

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
    virtual void SteppingBatchAction();

    int run_count() { return frun_count.GetValue(); }

    int event_count() { return fevent_count.GetValue(); }

    int track_count() { return ftrack_count.GetValue(); }

    int step_count() { return fstep_count.GetValue(); }

    void set_run_count(int i) { frun_count = i; }

    void set_event_count(int i) { fevent_count = i; }

    void set_track_count(int i) { ftrack_count = i; }

    void set_step_count(int i) { fstep_count = i; }


    G4Accumulable<int> frun_count;
    G4Accumulable<int> fevent_count;
    G4Accumulable<int> ftrack_count;
    G4Accumulable<int> fstep_count;

    /*int run_count;
    int event_count;
    int track_count;
    int step_count;
     */
    double duration;
    std::chrono::steady_clock::time_point start_time;
    std::chrono::steady_clock::time_point stop_time;
};

#endif // GamSimulationStatisticsActor_h
