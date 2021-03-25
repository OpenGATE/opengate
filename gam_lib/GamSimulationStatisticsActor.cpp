/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */


#include <chrono>
#include <vector>
#include <iomanip>
#include <iostream>
#include <sstream>
#include "G4AccumulableManager.hh"
#include "GamSimulationStatisticsActor.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"

G4Mutex GamSimulationStatisticsActorMutex = G4MUTEX_INITIALIZER;


GamSimulationStatisticsActor::GamSimulationStatisticsActor(py::dict &user_info)
        : GamVActor(user_info),
          fRunCount("Run", 0),
          fEventCount("Event", 0),
          fTrackCount("Track", 0),
          fStepCount("Step", 0),
          fTrackTypes("TrackType") {

    DDD("Actor constructor");

    fActions.push_back("BeginOfRunAction");
    fActions.push_back("EndOfRunAction");
    fActions.push_back("PreUserTrackingAction");
    fActions.push_back("SteppingAction");
    fDuration = 0;
    fTrackTypesFlag = DictBool(user_info, "track_types_flag");
    track_test = 0;


}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    fStartTime = std::chrono::system_clock::now();
    fStartTimeDuration = std::chrono::steady_clock::now();
    DDD("StartSimulationAction");
    // FIXME FIXME FIXME


    fRunCount.Reset();
    fEventCount.Reset();
    fTrackCount.Reset();
    fStepCount.Reset();
    fTrackTypes.Reset();


    G4AccumulableManager *accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->RegisterAccumulable(fRunCount);
    accumulableManager->RegisterAccumulable(fEventCount);
    accumulableManager->RegisterAccumulable(fTrackCount);
    accumulableManager->RegisterAccumulable(fStepCount);
    accumulableManager->RegisterAccumulable(&fTrackTypes);

}

// Called when the simulation end
void GamSimulationStatisticsActor::EndSimulationAction() {
    DDD("EndSimulationAction");
    fStopTimeDuration = std::chrono::steady_clock::now();
    fStopTime = std::chrono::system_clock::now();
    fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTimeDuration - fStartTimeDuration).count();
    fDuration = fDuration * CLHEP::microsecond;

    G4AccumulableManager *accumulableManager = G4AccumulableManager::Instance();
    DDD("Merge");
    DDD(accumulableManager->GetNofAccumulables());
    DDD(G4Threading::IsWorkerThread());
    accumulableManager->Merge();
    DDD("aafter merge");

    CreateCounts();
    DDD(track_test);
}

void GamSimulationStatisticsActor::CreateCounts() {
    fCounts["run_count"] = fRunCount.GetValue();
    fCounts["event_count"] = fEventCount.GetValue();
    fCounts["track_count"] = fTrackCount.GetValue();
    fCounts["step_count"] = fStepCount.GetValue();
    fCounts["duration"] = fDuration;
    {
        std::stringstream ss;
        auto t_c = std::chrono::system_clock::to_time_t(fStartTime);
        ss << std::ctime(&t_c);
        fCounts["start_time"] = ss.str();
    }
    {
        std::stringstream ss;
        auto t_c = std::chrono::system_clock::to_time_t(fStopTime);
        ss << std::ctime(&t_c);
        fCounts["stop_time"] = ss.str();
    }
    if (fTrackTypesFlag) {
        fCounts["track_types"] = fTrackTypes.GetValue();
    } else {
        fCounts["track_types"] = "";
    }
}

// Called every time a Run starts
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run * /*run*/) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    // FIXME todo later ?
    // start_time = std::chrono::steady_clock::now();


   
    /*
    G4AccumulableManager *accumulableManager = G4AccumulableManager::Instance();
    accumulableManager->RegisterAccumulable(fRunCount);
    accumulableManager->RegisterAccumulable(fEventCount);
    accumulableManager->RegisterAccumulable(fTrackCount);
    accumulableManager->RegisterAccumulable(fStepCount);
    accumulableManager->RegisterAccumulable(&fTrackTypes);
    */
}

// Called every time a Run ends
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fRunCount++;
    fEventCount += run->GetNumberOfEvent();
    DDD(fTrackTypes.GetValue());
    DDD(this);
    int n = 0;
    for (auto item:fTrackTypes.fTrackTypes) {
        n += py::int_(item.second);
    }


    G4AccumulableManager *accumulableManager = G4AccumulableManager::Instance();
    DDD("Merge");
    DDD(accumulableManager->GetNofAccumulables());
    DDD(G4Threading::IsWorkerThread());
    accumulableManager->Merge();
    DDD("aafter merge");

    DDD(n);
    DDD(fTrackCount.GetValue());
    DDD(track_test);
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track *track) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fTrackCount++;
    if (fTrackTypesFlag) {
        auto p = track->GetParticleDefinition()->GetParticleName();
        fTrackTypes.fTrackTypes[p]++;
    }
    //DDD(fTrackCount.GetValue());
    track_test ++;
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingAction(G4Step *, G4TouchableHistory *) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fStepCount++;
}
