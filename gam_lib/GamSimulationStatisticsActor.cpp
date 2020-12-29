/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <chrono>
#include <vector>
#include "G4AccumulableManager.hh"
#include "GamSimulationStatisticsActor.h"
#include "GamHelpers.h"

GamSimulationStatisticsActor::GamSimulationStatisticsActor(std::string type_name)
        : GamVActor(type_name),
          frun_count("Run", 0),
          fevent_count("Event", 0),
          ftrack_count("Track", 0),
          fstep_count("Step", 0) {

    actions.push_back("BeginOfRunAction");
    actions.push_back("EndOfRunAction");
    //actions.push_back("BeginOfEventAction");
    actions.push_back("PreUserTrackingAction");
    actions.push_back("ProcessHits");
}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    start_time = std::chrono::steady_clock::now();
    DDD("Stat action Start simulation");
    frun_count.Reset();
    fevent_count.Reset();
    ftrack_count.Reset();
    fstep_count.Reset();
    DDD("Register accumulable");
    G4AccumulableManager *accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->RegisterAccumulable(frun_count);
    accumulableManager->RegisterAccumulable(fevent_count);
    accumulableManager->RegisterAccumulable(ftrack_count);
    accumulableManager->RegisterAccumulable(fstep_count);
}

// Called when the simulation end
void GamSimulationStatisticsActor::EndSimulationAction() {
    stop_time = std::chrono::steady_clock::now();
    duration = std::chrono::duration_cast<std::chrono::microseconds>(stop_time - start_time).count();
    duration = duration * CLHEP::microsecond;
}

// Called every time a Run starts
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run *r/*run*/) {
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    //if (run_count == 0)
    //    start_time = std::chrono::steady_clock::now();
}

// Called every time a Run starts
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    frun_count++;
    fevent_count += run->GetNumberOfEvent();
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track * /*track*/) {
    ftrack_count++;
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingBatchAction() {
    fstep_count++;
}

