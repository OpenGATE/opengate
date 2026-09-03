/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSimulationStatisticsActor.h"
#include "GateHelpersDict.h"
#include <chrono>

G4Mutex GateSimulationStatisticsActorMutex = G4MUTEX_INITIALIZER;

using namespace pybind11::literals;

GateSimulationStatisticsActor::GateSimulationStatisticsActor(
    py::dict &user_info)
    : GateVActor(user_info, true) {
  fActions.insert("StartSimulationAction");
  fActions.insert("BeginOfRunAction");
  fActions.insert("BeginOfEventAction");
  fActions.insert("PreUserTrackingAction");
  fActions.insert("SteppingAction");
  fActions.insert("EndOfRunAction");
  fActions.insert("EndOfSimulationWorkerAction");
  fActions.insert("EndSimulationAction");
  fDuration = 0;
  fTrackTypesFlag = false;
  fInitDuration = 0;
  fStartRunTimeIsSet = false;
}

GateSimulationStatisticsActor::~GateSimulationStatisticsActor() = default;

void GateSimulationStatisticsActor::InitializeUserInfo(py::dict &user_info) {
  // IMPORTANT: call the base class method
  GateVActor::InitializeUserInfo(user_info);

  fTrackTypesFlag = DictGetBool(user_info, "track_types_flag");
}

void GateSimulationStatisticsActor::StartSimulationAction() {
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
  fCounts["runs"] = 0;
  fCounts["events"] = 0;
  fCounts["tracks"] = 0;
  fCounts["steps"] = 0;
  fCountsD.clear();
  fCountsStr.clear();
  fTrackTypes.clear();
  fCountsCurrentRun.clear();
  fCountsDCurrentRun.clear();
  fCountsStrCurrentRun.clear();
  fTrackTypesCurrentRun.clear();
}

py::dict GateSimulationStatisticsActor::GetCounts() {
  auto dd = py::dict(
      "runs"_a = fCounts["runs"], "events"_a = fCounts["events"],
      "tracks"_a = fCounts["tracks"], "steps"_a = fCounts["steps"],
      "duration"_a = fCountsD["duration"], "init"_a = fCountsD["init"],
      "start_time"_a = fCountsStr["start_time"],
      "stop_time"_a = fCountsStr["stop_time"], "track_types"_a = fTrackTypes);
  return dd;
}

py::dict GateSimulationStatisticsActor::GetCountsCurrentRun() {
  auto dd = py::dict("runs"_a = fCountsCurrentRun["runs"],
                     "events"_a = fCountsCurrentRun["events"],
                     "tracks"_a = fCountsCurrentRun["tracks"],
                     "steps"_a = fCountsCurrentRun["steps"],
                     "duration"_a = fCountsDCurrentRun["duration"],
                     "init"_a = fCountsDCurrentRun["init"],
                     "start_time"_a = fCountsStrCurrentRun["start_time"],
                     "stop_time"_a = fCountsStrCurrentRun["stop_time"],
                     "track_types"_a = fTrackTypesCurrentRun);
  return dd;
}

void GateSimulationStatisticsActor::BeginOfRunActionMasterThread(int run_id) {
  fCountsCurrentRun.clear();
  fCountsCurrentRun["runs"] = 0;
  fCountsCurrentRun["events"] = 0;
  fCountsCurrentRun["tracks"] = 0;
  fCountsCurrentRun["steps"] = 0;
  fCountsDCurrentRun.clear();
  fCountsStrCurrentRun.clear();
  fTrackTypesCurrentRun.clear();
  fStartCurrentRunTime = std::chrono::system_clock::now();
}

void GateSimulationStatisticsActor::BeginOfRunAction(const G4Run *run) {
  // Called every time a run starts
  if (run->GetRunID() == 0) {
    if (!G4Threading::IsMultithreadedApplication())
      fStartRunTime = std::chrono::system_clock::now();
    else {
      if (!fStartRunTimeIsSet) {
        // StartRunTime for the first run to start
        G4AutoLock mutex(&GateSimulationStatisticsActorMutex);
        fStartRunTime = std::chrono::system_clock::now();
        fStartRunTimeIsSet = true;
      }
    }
  }
  threadLocal_t &data = threadLocalData.Get();
  if (run->GetRunID() == 0) {
    // Historical simulation-wide counters. These accumulate across all runs
    // and are merged only once in EndOfSimulationWorkerAction().
    data.fRunCount = 0;
    data.fEventCount = 0;
    data.fTrackCount = 0;
    data.fStepCount = 0;
    data.fTrackTypes.clear();
  }
  // Dedicated per-run counters. These are reset for every run and merged into
  // the per-run storage only.
  data.fCurrentRunCount = 0;
  data.fCurrentRunEventCount = 0;
  data.fCurrentRunTrackCount = 0;
  data.fCurrentRunStepCount = 0;
  data.fCurrentRunTrackTypes.clear();
}

void GateSimulationStatisticsActor::PreUserTrackingAction(
    const G4Track *track) {
  // Called every time a track starts
  threadLocal_t &data = threadLocalData.Get();
  data.fTrackCount++;
  data.fCurrentRunTrackCount++;
  if (fTrackTypesFlag) {
    auto p = track->GetParticleDefinition()->GetParticleName();
    data.fTrackTypes[p]++;
    data.fCurrentRunTrackTypes[p]++;
  }
}

void GateSimulationStatisticsActor::SteppingAction(G4Step *) {
  // Called every step
  threadLocal_t &data = threadLocalData.Get();
  data.fStepCount++;
  data.fCurrentRunStepCount++;
}

void GateSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
  // Called every time a run ends
  const int run_id = run->GetRunID();
  threadLocal_t &data = threadLocalData.Get();
  data.fRunCount++;
  data.fEventCount += run->GetNumberOfEvent();
  data.fCurrentRunCount++;
  data.fCurrentRunEventCount += run->GetNumberOfEvent();

  G4AutoLock mutex(&GateSimulationStatisticsActorMutex);
  fCountsCurrentRun["runs"] += data.fCurrentRunCount;
  fCountsCurrentRun["events"] += data.fCurrentRunEventCount;
  fCountsCurrentRun["tracks"] += data.fCurrentRunTrackCount;
  fCountsCurrentRun["steps"] += data.fCurrentRunStepCount;
  if (fTrackTypesFlag) {
    for (const auto &v : data.fCurrentRunTrackTypes) {
      fTrackTypesCurrentRun[v.first] += v.second;
    }
  }
}

void GateSimulationStatisticsActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  // Historical merged statistics path: accumulate the simulation-wide counters
  // exactly as before. Per-run counters are handled in EndOfRunAction().
  G4AutoLock mutex(&GateSimulationStatisticsActorMutex);
  threadLocal_t &data = threadLocalData.Get();
  fCounts["runs"] += data.fRunCount;
  fCounts["events"] += data.fEventCount;
  fCounts["tracks"] += data.fTrackCount;
  fCounts["steps"] += data.fStepCount;
  if (fTrackTypesFlag) {
    for (const auto &v : data.fTrackTypes) {
      if (fTrackTypes.count(v.first) == 0)
        fTrackTypes[v.first] = 0;
      fTrackTypes[v.first] = v.second + fTrackTypes[v.first];
    }
  }
}

int GateSimulationStatisticsActor::EndOfRunActionMasterThread(int run_id) {
  fStopCurrentRunTime = std::chrono::system_clock::now();
  const auto run_duration =
      std::chrono::duration_cast<std::chrono::microseconds>(
          fStopCurrentRunTime - fStartCurrentRunTime);
  fCountsDCurrentRun["duration"] =
      static_cast<double>(run_duration.count()) * CLHEP::microsecond;
  fCountsDCurrentRun["init"] = 0.0;

  {
    auto t_c = std::chrono::system_clock::to_time_t(fStartCurrentRunTime);
    std::string s = std::ctime(&t_c);
    if (!s.empty() && s.back() == '\n') {
      s.pop_back();
    }
    fCountsStrCurrentRun["start_time"] = s;
  }
  {
    auto t_c = std::chrono::system_clock::to_time_t(fStopCurrentRunTime);
    std::string s = std::ctime(&t_c);
    if (!s.empty() && s.back() == '\n') {
      s.pop_back();
    }
    fCountsStrCurrentRun["stop_time"] = s;
  }
  return 0;
}

void GateSimulationStatisticsActor::EndSimulationAction() {
  // Called when the simulation end (only by the master thread)
  fStopTime = std::chrono::system_clock::now();
  fDuration =
      static_cast<double>(std::chrono::duration_cast<std::chrono::microseconds>(
                              fStopTime - fStartRunTime)
                              .count());
  fInitDuration =
      static_cast<double>(std::chrono::duration_cast<std::chrono::microseconds>(
                              fStartRunTime - fStartTime)
                              .count());
  fDuration = fDuration * CLHEP::microsecond;
  fInitDuration = fInitDuration * CLHEP::microsecond;
  fCountsD["duration"] = fDuration;
  fCountsD["init"] = fInitDuration;
  {
    auto t_c = std::chrono::system_clock::to_time_t(fStartTime);
    std::string s = std::ctime(&t_c);
    if (!s.empty() && s.back() == '\n') {
      s.pop_back();
    }
    fCountsStr["start_time"] = s;
  }
  {
    auto t_c = std::chrono::system_clock::to_time_t(fStopTime);
    std::string s = std::ctime(&t_c);
    if (!s.empty() && s.back() == '\n') {
      s.pop_back();
    }
    fCountsStr["stop_time"] = s;
  }
}
