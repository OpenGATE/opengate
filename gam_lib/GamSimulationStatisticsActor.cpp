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
    fActions.insert("BeginOfRunAction");
    fActions.insert("BeginOfEventAction");
    fActions.insert("PreUserTrackingAction");
    fActions.insert("SteppingAction");
    fActions.insert("EndOfRunAction");
    fActions.insert("EndOfSimulationWorkerAction");
    fActions.insert("EndSimulationAction");
    fDuration = 0;
    fTrackTypesFlag = DictBool(user_info, "track_types_flag");
}

GamSimulationStatisticsActor::~GamSimulationStatisticsActor() = default;

// Called when the simulation start
void GamSimulationStatisticsActor::StartSimulationAction() {
    fStartTime = std::chrono::system_clock::now();
    DDD(fTrackTypesFlag);
    fCounts["run_count"] = 0;
    fCounts["event_count"] = 0;
    fCounts["track_count"] = 0;
    fCounts["step_count"] = 0;
    //fCounts["track_types"] = std::map<std::string, long int>;
}

// Called when the simulation end
void GamSimulationStatisticsActor::EndSimulationAction() {
    fStopTime = std::chrono::system_clock::now();
    fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTime - fStartTime).count();
    fDuration = fDuration * CLHEP::microsecond;

    //CreateCounts();
    fCounts["duration"] = fDuration;
    fCounts["track_types"] = fTrackTypes;
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

}

void GamSimulationStatisticsActor::CreateCounts() {
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    DDD("CreateCounts");
    threadLocal_t &data = threadLocalData.Get();
    fCounts["run_count"] = data.fRunCount + DictInt(fCounts, "run_count");
    fCounts["event_count"] = data.fEventCount + DictInt(fCounts, "event_count");
    fCounts["track_count"] = data.fTrackCount + DictInt(fCounts, "track_count");
    fCounts["step_count"] = data.fStepCount + DictInt(fCounts, "step_count");
    //fCounts["duration"] = fDuration;
    if (fTrackTypesFlag) {
        //  fCounts["track_types"] = data.fTrackTypes;
        //fTrackTypes.merge(data.fTrackTypes);
        for (auto v: data.fTrackTypes) {
            DDD(v.first);
            DDD(v.second);
            if (fTrackTypes.count(v.first) == 0) fTrackTypes[v.first] = 0;
            fTrackTypes[v.first] = v.second + fTrackTypes[v.first];
        }
    } else {
        fCounts["track_types"] = "";
    }
}

// Called every time a Run starts
void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run *run) {
    //G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    // It is better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation)
    // FIXME todo later ?
    // start_time = std::chrono::steady_clock::now();
    if (run->GetRunID() == 0) {
        DDD("Init thread local data");
        threadLocal_t &data = threadLocalData.Get();
        data.fRunCount = 0;
        data.fEventCount = 0;
        data.fTrackCount = 0;
        data.fStepCount = 0;
    }

}

// Called every time a Run ends
void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    //G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    threadLocal_t &data = threadLocalData.Get();
    data.fRunCount++;
    data.fEventCount += run->GetNumberOfEvent();
    DDD(data.fRunCount);
    DDD(data.fEventCount);
    DDD(data.fTrackCount);
    DDD(data.fStepCount);
    DDD(data.fTrackTypes["e-"]);
    DDD(data.fTrackTypes["gamma"]);
}

// Called every time a Run ends
void GamSimulationStatisticsActor::EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {
    DDD("EndOfSimulationWorkerAction");
    CreateCounts();
}

// Called every time a Track starts
void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track *track) {
    //G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    threadLocal_t &data = threadLocalData.Get();
    data.fTrackCount++;
    if (fTrackTypesFlag) {
        auto p = track->GetParticleDefinition()->GetParticleName();
        if (p == "e-") {
            //DDD("ici");
            //DDD(data.fTrackTypes[p]);
        }
        data.fTrackTypes[p]++;
        /*DDD(track->GetTrackID());
        DDD(track->GetTrackStatus());*/
    }
}

// Called every time a batch of step must be processed
void GamSimulationStatisticsActor::SteppingAction(G4Step *, G4TouchableHistory *) {
    //G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    threadLocal_t &data = threadLocalData.Get();
    data.fStepCount++;
}
