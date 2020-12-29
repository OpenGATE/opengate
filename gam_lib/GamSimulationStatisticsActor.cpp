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

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    start_time = std::chrono::steady_clock::now();

    DDD("Start simulation");

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
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run *r/*run*/) {

    /*
    DDD("Start simulation analysis man");
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->OpenFile("stats.txt");
    analysisManager->CreateNtuple("stats", "Statistics");
    analysisManager->CreateNtupleDColumn("Runs");
    analysisManager->CreateNtupleDColumn("Events");
    analysisManager->CreateNtupleDColumn("Tracks");
    analysisManager->CreateNtupleDColumn("Steps");
    analysisManager->FinishNtuple();
    DDD("end manager");


    DDD("begin of run get analysis manager");
    //auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->FillNtupleDColumn(0, 1);
    DDD("after get analysis manager");
     */


    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    if (run_count == 0)
        start_time = std::chrono::steady_clock::now();
    run_count++;
    DDD(r->GetRunID());
}

// Called every time a Run starts
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    DDD(run->GetRunID());

    /*
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->FillNtupleDColumn(1, run->GetNumberOfEvent());

    //auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->Write();
    analysisManager->CloseFile();
     */

    frun_count++;
    fevent_count += run->GetNumberOfEvent();

    DDD(frun_count.GetValue());
    DDD(fevent_count.GetValue());
    DDD(ftrack_count.GetValue());
    DDD(fstep_count.GetValue());

    //auto accumulableManager = G4AccumulableManager::Instance();
    //accumulableManager->Merge();
    //DDD(fevent_count.GetValue());

    event_count = run->GetNumberOfEvent();
}

// Called every time an Event starts
void GamSimulationStatisticsActor::BeginOfEventAction(const G4Event *e /*event*/) {
    //event_count++;
    //DDD(e->GetEventID());
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track * /*track*/) {

    /*
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->FillNtupleDColumn(2, 1);
    */
    ftrack_count++;
    track_count++;
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingBatchAction() {
    fstep_count++;
    step_count++;
    DDD(fstep_count.GetValue());
}

