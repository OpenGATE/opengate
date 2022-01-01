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

void GamSimulationStatisticsActor::StartSimulationAction() {
    // Called when the simulation start
    // It may be better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // (it is only significant for short simulation).
    // However, it is simpler here because it is only run by master thread
    // (while BeginOfRunAction is executed by all threads)
    fStartTime = std::chrono::system_clock::now();

    // initialise the counts
    fCounts["run_count"] = 0;
    fCounts["event_count"] = 0;
    fCounts["track_count"] = 0;
    fCounts["step_count"] = 0;
}

void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run *run) {
    // Called every time a run starts
    if (run->GetRunID() == 0) {
        // Initialise the thread local data
        threadLocal_t &data = threadLocalData.Get();
        data.fRunCount = 0;
        data.fEventCount = 0;
        data.fTrackCount = 0;
        data.fStepCount = 0;
    }
}

void GamSimulationStatisticsActor::PreUserTrackingAction(const G4Track *track) {
    // Called every time a track starts
    threadLocal_t &data = threadLocalData.Get();
    data.fTrackCount++;
    if (fTrackTypesFlag) {
        auto p = track->GetParticleDefinition()->GetParticleName();
        data.fTrackTypes[p]++;
    }
}

void GamSimulationStatisticsActor::SteppingAction(G4Step *, G4TouchableHistory *) {
    // Called every step
    threadLocalData.Get().fStepCount++;
}

void GamSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
    // Called every time a run ends
    threadLocal_t &data = threadLocalData.Get();
    data.fRunCount++;
    data.fEventCount += run->GetNumberOfEvent();
}

void GamSimulationStatisticsActor::EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {
    // Called every time the simulation is about to end, by ALL threads
    // So, the data are merged (need a mutex lock)
    G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
    threadLocal_t &data = threadLocalData.Get();
    fCounts["run_count"] = data.fRunCount + DictInt(fCounts, "run_count");
    fCounts["event_count"] = data.fEventCount + DictInt(fCounts, "event_count");
    fCounts["track_count"] = data.fTrackCount + DictInt(fCounts, "track_count");
    fCounts["step_count"] = data.fStepCount + DictInt(fCounts, "step_count");
    if (fTrackTypesFlag) {
        for (auto v: data.fTrackTypes) {
            if (fTrackTypes.count(v.first) == 0) fTrackTypes[v.first] = 0;
            fTrackTypes[v.first] = v.second + fTrackTypes[v.first];
        }
    } else {
        fCounts["track_types"] = "";
    }
}

void GamSimulationStatisticsActor::EndSimulationAction() {
    // Called when the simulation end (only by the master thread)
    fStopTime = std::chrono::system_clock::now();
    fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTime - fStartTime).count();
    fDuration = fDuration * CLHEP::microsecond;
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
