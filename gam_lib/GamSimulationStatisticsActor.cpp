/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <chrono>
#include "GamSimulationStatisticsActor.h"


GamSimulationStatisticsActor::GamSimulationStatisticsActor(std::string type_name) : GamVActor(type_name) {
    run_count = 0;
    event_count = 0;
    track_count = 0;
    step_count = 0;
}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    start_time = std::chrono::steady_clock::now();
    run_count = 0;
    event_count = 0;
    track_count = 0;
    step_count = 0;
}

// Called when the simulation end
void GamSimulationStatisticsActor::EndSimulationAction() {
    stop_time = std::chrono::steady_clock::now();
    duration = std::chrono::duration_cast<std::chrono::microseconds>(stop_time - start_time).count();
    duration = duration * CLHEP::microsecond;
}

// Called every time a Run starts
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run * /*run*/) {
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    if (run_count == 0)
        start_time = std::chrono::steady_clock::now();
    run_count++;
}

// Called every time a Run starts
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run * /*run*/) {

}

// Called every time an Event starts
void GamSimulationStatisticsActor::BeginOfEventAction(const G4Event * /*event*/) {
    event_count++;
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track * /*track*/) {
    track_count++;
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingBatchAction() {
    step_count++;
}

