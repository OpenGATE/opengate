/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDebugSource.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "fmt/core.h"
#include <G4Threading.hh>
#include <G4UnitsTable.hh>
#include <pybind11/pytypes.h>

GateDebugSource::GateDebugSource() : GateVSource() {
  DDD("GateDebugSource constructor");
}

GateDebugSource::~GateDebugSource() { DDD("GateDebugSource destructor"); }

void GateDebugSource::CleanWorkerThread() {
  DDD("GateDebugSource::CleanWorkerThread");
}

void GateDebugSource::InitializeUserInfo(py::dict &user_info) {
  DDD("GateDebugSource::InitializeUserInfo");
  GateVSource::InitializeUserInfo(user_info);
  auto &ld = fThreadLocalDataDebugSource.Get();
  ld.debug_value = DictGetDouble(user_info, "debug_value");
}

void GateDebugSource::UpdateActivity(const double time) {
  DDD("GateDebugSource::UpdateActivity");
  GateVSource::UpdateActivity(time);
}

double GateDebugSource::PrepareNextTime(const double current_simulation_time,
                                        double NumberOfGeneratedEvents) {
  DDD("GateDebugSource::PrepareNextTime", " ",
      G4BestUnit(current_simulation_time, "Time"), " ",
      NumberOfGeneratedEvents);
  return GateVSource::PrepareNextTime(current_simulation_time,
                                      NumberOfGeneratedEvents);
}

void GateDebugSource::PrepareNextRun() {
  DDD("GateDebugSource::PrepareNextRun");
  GateVSource::PrepareNextRun();
}

void GateDebugSource::GeneratePrimaries(G4Event *event,
                                        const double current_simulation_time) {
  DDD("GateDebugSource::GeneratePrimaries", " ", event->GetEventID(), " ",
      fMaxN);
  auto &l = GetThreadLocalData();
  l.fNumberOfGeneratedEvents++;
  auto &ld = fThreadLocalDataDebugSource.Get();
  ld.debug_value += 1;
  DDD("debug value = ", ld.debug_value);
}

double GateDebugSource::GetDebugValue() {
  auto &ld = fThreadLocalDataDebugSource.Get();
  DDD("GateDebugSource::GetDebugValue ", ld.debug_value)
  return ld.debug_value;
}
