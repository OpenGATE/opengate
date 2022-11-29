/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAcceptanceAngleTesterManager.h"
#include "G4RunManager.hh"
#include "GateAcceptanceAngleTester.h"
#include "GateHelpersDict.h"

GateAcceptanceAngleTesterManager::GateAcceptanceAngleTesterManager() {
  fEnabledFlag = false;
  fNotAcceptedEvents = 0;
  fAALastRunId = -1;
  fMode = AASkipEvent;
}

void GateAcceptanceAngleTesterManager::Initialize(py::dict puser_info,
                                                  bool is_iso) {
  fAcceptanceAngleVolumeNames = DictGetVecStr(puser_info, "volumes");
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();
  if (not fEnabledFlag)
    return;
  // (we cannot use py::dict here as it is lost at the end of the function)
  fAcceptanceAngleParam = DictToMap(puser_info);
  DDD("GateAcceptanceAngleTesterManager::Initialize");
  DDDV(fAcceptanceAngleVolumeNames);
  auto s = DictGetStr(puser_info, "skip_mode");
  fMode = AAUndefined;
  if (s == "EnergyZero")
    fMode = AAEnergyZero;
  if (s == "SkipEvents")
    fMode = AASkipEvent;
  if (fMode == AAUndefined) {
    std::ostringstream oss;
    oss << "Unknown '" << s << "' mode for GateAcceptanceAngleTesterManager. "
        << "Expected: EnergyZero or SkipEvents";
    Fatal(oss.str());
  }

  // Cannot use SkipEvent with non iso source
  if (not is_iso and fMode == AASkipEvent) {
    std::ostringstream oss;
    oss << "Cannot use 'SkipEvent' mode without 'iso' direction type";
    Fatal(oss.str());
  }
}

void GateAcceptanceAngleTesterManager::InitializeAcceptanceAngle() {
  DDD("void GateAcceptanceAngleTesterManager::InitializeAcceptanceAngle()");
  if (not fEnabledFlag)
    return;
  // Create the testers (only the first time)
  if (fAATesters.empty()) {
    for (const auto &name : fAcceptanceAngleVolumeNames) {
      auto *t = new GateAcceptanceAngleTester(name, fAcceptanceAngleParam);
      fAATesters.push_back(t);
    }
  }

  // Update the transform (all runs!)
  for (auto *t : fAATesters)
    t->UpdateTransform();

  // store the ID of this Run
  fAALastRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();
}

unsigned long
GateAcceptanceAngleTesterManager::GetNumberOfNotAcceptedEvents() const {
  return fNotAcceptedEvents;
}

bool GateAcceptanceAngleTesterManager::TestIfAccept(
    const G4ThreeVector &position, const G4ThreeVector &momentum_direction) {
  if (!fEnabledFlag)
    return true;
  // Loop on all volume to check if it is accepted
  for (auto *tester : fAATesters) {
    bool accept = tester->TestIfAccept(position, momentum_direction);
    if (not accept) {
      fNotAcceptedEvents++;
      return false;
    }
  }
  return true;
}

void GateAcceptanceAngleTesterManager::StartAcceptLoop() {
  if (not fEnabledFlag)
    return;
  fNotAcceptedEvents = 0;
  if (fAALastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
    InitializeAcceptanceAngle();
}
