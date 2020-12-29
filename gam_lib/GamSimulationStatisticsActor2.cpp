/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <chrono>
#include <vector>
#include "GamSimulationStatisticsActor2.h"
#include "GamHelpers.h"

GamSimulationStatisticsActor2::GamSimulationStatisticsActor2(std::string type_name) : GamVActor(type_name) {
    run_count = 0;
    event_count = 0;
    track_count = 0;
    step_count = 0;
    actions.push_back("BeginOfRunAction");
    actions.push_back("EndOfRunAction");
    //actions.push_back("BeginOfEventAction");
    actions.push_back("PreUserTrackingAction");
    actions.push_back("ProcessHits");
}

GamSimulationStatisticsActor2::~GamSimulationStatisticsActor2() = default;

// Called when the simulation start
void GamSimulationStatisticsActor2::StartSimulationAction() {
    start_time = std::chrono::steady_clock::now();
    run_count = 0;
    event_count = 0;
    track_count = 0;
    step_count = 0;
}

// Called when the simulation end
void GamSimulationStatisticsActor2::EndSimulationAction() {
    stop_time = std::chrono::steady_clock::now();
    duration = std::chrono::duration_cast<std::chrono::microseconds>(stop_time - start_time).count();
    duration = duration * CLHEP::microsecond;
}

// Called every time a Run starts
void GamSimulationStatisticsActor2::BeginOfRunAction(const G4Run *r/*run*/) {
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    if (run_count == 0)
        start_time = std::chrono::steady_clock::now();
    run_count++;
    DDD(r->GetRunID());
}

// Called every time a Run starts
void GamSimulationStatisticsActor2::EndOfRunAction(const G4Run * run) {
    DDD(run->GetRunID());
    event_count = run->GetNumberOfEvent();
}

// Called every time an Event starts
void GamSimulationStatisticsActor2::BeginOfEventAction(const G4Event *e /*event*/) {
    //event_count++;
    //DDD(e->GetEventID());
}

// Called every time a Track starts
void GamSimulationStatisticsActor2::PreUserTrackingAction(const G4Track * /*track*/) {
    track_count++;
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor2::SteppingBatchAction() {
    step_count++;
}

