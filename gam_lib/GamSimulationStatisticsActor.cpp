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
#include "GamSimulationStatisticsActor.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"

G4Mutex GamSimulationStatisticsActorMutex = G4MUTEX_INITIALIZER;


GamSimulationStatisticsActor::GamSimulationStatisticsActor(py::dict &user_info)
    : GamVActor(user_info) {
    fActions.insert("StartSimulationAction");
    fActions.insert("EndSimulationAction");
    fActions.insert("BeginOfRunAction");
    fActions.insert("BeginOfEventAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("SteppingAction");
    fDuration = 0;
    fRunCount = 0;
    fEventCount = 0;
    fTrackCount = 0;
    fStepCount = 0;
    fTrackTypesFlag = DictBool(user_info, "track_types_flag");
}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    fStartTime = std::chrono::system_clock::now();
    //fStartTimeDuration = std::chrono::steady_clock::now();
}

// Called when the simulation end
void GamSimulationStatisticsActor::EndSimulationAction() {
    //fStopTimeDuration = std::chrono::steady_clock::now();
    fStopTime = std::chrono::system_clock::now();
    //fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTimeDuration - fStartTimeDuration).count();
    fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTime - fStartTime).count();
    fDuration = fDuration * CLHEP::microsecond;
    CreateCounts();
}

void GamSimulationStatisticsActor::CreateCounts() {
    fCounts["run_count"] = fRunCount;
    fCounts["event_count"] = fEventCount;
    fCounts["track_count"] = fTrackCount;
    fCounts["step_count"] = fStepCount;
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
        fCounts["track_types"] = fTrackTypes;
    } else {
        fCounts["track_types"] = "";
    }
}

// Called every time a Run starts
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run * /*run*/) {
    //G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    // FIXME todo later ?
    // start_time = std::chrono::steady_clock::now();
}

// Called every time a Run ends
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fRunCount++;
    fEventCount += run->GetNumberOfEvent();
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track *track) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fTrackCount++;
    if (fTrackTypesFlag) {
        auto p = track->GetParticleDefinition()->GetParticleName();
        fTrackTypes[p]++;
    }
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingAction(G4Step *, G4TouchableHistory *) {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    fStepCount++;
}
