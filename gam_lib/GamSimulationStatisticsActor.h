/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSimulationStatisticsActor_h
#define GamSimulationStatisticsActor_h

#include "GamVActor.h"

class GamSimulationStatisticsActor : public GamVActor {

public:

    explicit GamSimulationStatisticsActor(std::string type_name);

    virtual ~GamSimulationStatisticsActor();

    // Called when the simulation start
    virtual void StartSimulationAction();

    // Called when the simulation end
    virtual void EndSimulationAction();

    // Called every time a Run starts
    virtual void BeginOfRunAction(const G4Run *run);

    virtual void EndOfRunAction(const G4Run *run);

    // Called every time an Event starts
    virtual void BeginOfEventAction(const G4Event *event);

    // Called every time a Track starts
    virtual void PreUserTrackingAction(const G4Track *track);

    // Called every time a batch of step must be processed
    virtual void SteppingBatchAction();

    int run_count;
    int event_count;
    int track_count;
    int step_count;
    double duration;
    std::chrono::steady_clock::time_point start_time;
    std::chrono::steady_clock::time_point stop_time;
};

#endif // GamSimulationStatisticsActor_h
