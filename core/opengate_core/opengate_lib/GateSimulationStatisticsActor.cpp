/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSimulationStatisticsActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
// For DEBUGGING only (see below) - remove again
#include "G4UnitsTable.hh"
#include "G4Electron.hh"
#include "G4VProcess.hh"

#include <chrono>
#include <iostream>
#include <sstream>

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
    // Initialise the thread local data
    threadLocal_t &data = threadLocalData.Get();
    data.fRunCount = 0;
    data.fEventCount = 0;
    data.fTrackCount = 0;
    data.fStepCount = 0;
  }
}

void GateSimulationStatisticsActor::PreUserTrackingAction(
    const G4Track *track) {
  // Called every time a track starts
  threadLocal_t &data = threadLocalData.Get();
  data.fTrackCount++;
  if (fTrackTypesFlag) {
    auto p = track->GetParticleDefinition()->GetParticleName();
    data.fTrackTypes[p]++;

    // For DEBUGGING only - remove
    // for electrons, print which process created them
    // to check if cuts work as expected
    if (track->GetParticleDefinition() == G4Electron::Definition()) {
      const G4VProcess* creator = track->GetCreatorProcess();
      const G4String proc = creator ? creator->GetProcessName() : "primary";
      const G4double ekin = track->GetKineticEnergy();
      std::cout << "  Ek=" << G4BestUnit(ekin,"Energy")
             << "  created by " << proc
             << "  parentID=" << track->GetParentID() << std::endl;
    }
  }
}

void GateSimulationStatisticsActor::SteppingAction(G4Step *) {
  // Called every step
  threadLocalData.Get().fStepCount++;
}

void GateSimulationStatisticsActor::EndOfRunAction(const G4Run *run) {
  // Called every time a run ends
  threadLocal_t &data = threadLocalData.Get();
  data.fRunCount++;
  data.fEventCount += run->GetNumberOfEvent();
}

void GateSimulationStatisticsActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  // Called every time the simulation is about to end, by ALL threads
  // So, the data are merged (need a mutex lock)
  G4AutoLock mutex(&GateSimulationStatisticsActorMutex);
  threadLocal_t &data = threadLocalData.Get();
  // merge all threads (need mutex)
  fCounts["runs"] += data.fRunCount;
  fCounts["events"] += data.fEventCount;
  fCounts["tracks"] += data.fTrackCount;
  fCounts["steps"] += data.fStepCount;
  if (fTrackTypesFlag) {
    for (auto v : data.fTrackTypes) {
      if (fTrackTypes.count(v.first) == 0)
        fTrackTypes[v.first] = 0;
      fTrackTypes[v.first] = v.second + fTrackTypes[v.first];
    }
  }
}

void GateSimulationStatisticsActor::EndSimulationAction() {
  // Called when the simulation end (only by the master thread)
  fStopTime = std::chrono::system_clock::now();
  fDuration = std::chrono::duration_cast<std::chrono::microseconds>(
                  fStopTime - fStartRunTime)
                  .count();
  fInitDuration = std::chrono::duration_cast<std::chrono::microseconds>(
                      fStartRunTime - fStartTime)
                      .count();
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
