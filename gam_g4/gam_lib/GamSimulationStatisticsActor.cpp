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
#include "GamHelpersDict.h"
#include "GamHelpers.h"

G4Mutex GamSimulationStatisticsActorMutex = G4MUTEX_INITIALIZER;

using namespace pybind11::literals;


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

    // Time measurement WARNING
    // It may be better to start time measurement at begin of (first) run,
    // because there is some time between StartSimulation and BeginOfRun
    // and because Gate used to do that.
    // However, for MT application, it is simpler to start here
    // because it is only run by master thread (while BeginOfRunAction is
    // executed by all threads). But, it means the measurement includes
    // the (relatively) high time needed to start all threads.
    fStartTime = std::chrono::system_clock::now();
    fStartRunTimeIsSet = false;

    // initialise the counts
    fCounts["run_count"] = 0;
    fCounts["event_count"] = 0;
    fCounts["track_count"] = 0;
    fCounts["step_count"] = 0;
}

py::dict GamSimulationStatisticsActor::GetCounts() {
    auto dd = py::dict("run_count"_a = fCounts["run_count"],
                       "event_count"_a = fCounts["event_count"],
                       "track_count"_a = fCounts["track_count"],
                       "step_count"_a = fCounts["step_count"],
                       "duration"_a = fCountsD["duration"],
                       "init"_a = fCountsD["init"],
                       "start_time"_a = fCountsStr["start_time"],
                       "stop_time"_a = fCountsStr["stop_time"],
                       "track_types"_a = fTrackTypes);
    return dd;
}


void GamSimulationStatisticsActor::BeginOfRunAction(const G4Run *run) {
    // Called every time a run starts
    if (run->GetRunID() == 0) {
        if (not G4Threading::IsMultithreadedApplication())
            fStartRunTime = std::chrono::system_clock::now();
        else {
            if (not fStartRunTimeIsSet) {
                // StartRunTime for the first run to start
                G4AutoLock mutex(&GamSimulationStatisticsActorMutex);
                fStartRunTime = std::chrono::system_clock::now();
                fStartRunTimeIsSet = true;
            }
        }
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
    // merge all threads (need mutex)
    fCounts["run_count"] += data.fRunCount;
    fCounts["event_count"] += data.fEventCount;
    fCounts["track_count"] += data.fTrackCount;
    fCounts["step_count"] += data.fStepCount;
    if (fTrackTypesFlag) {
        for (auto v: data.fTrackTypes) {
            if (fTrackTypes.count(v.first) == 0) fTrackTypes[v.first] = 0;
            fTrackTypes[v.first] = v.second + fTrackTypes[v.first];
        }
    }
}

void GamSimulationStatisticsActor::EndSimulationAction() {
    // Called when the simulation end (only by the master thread)
    fStopTime = std::chrono::system_clock::now();
    fDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStopTime - fStartRunTime).count();
    fInitDuration = std::chrono::duration_cast<std::chrono::microseconds>(fStartRunTime - fStartTime).count();
    fDuration = fDuration * CLHEP::microsecond;
    fInitDuration = fInitDuration * CLHEP::microsecond;
    fCountsD["duration"] = fDuration;
    fCountsD["init"] = fInitDuration;
    {
        std::stringstream ss;
        auto t_c = std::chrono::system_clock::to_time_t(fStartTime);
        ss << strtok(std::ctime(&t_c), "\n");
        fCountsStr["start_time"] = ss.str();
    }
    {
        std::stringstream ss;
        auto t_c = std::chrono::system_clock::to_time_t(fStopTime);
        ss << strtok(std::ctime(&t_c), "\n");
        fCountsStr["stop_time"] = ss.str();
    }
}
