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
  fPolicy = AASkipEvent;
  fMaxNotAcceptedEvents = 10000;
}

void GateAcceptanceAngleTesterManager::Initialize(py::dict puser_info,
                                                  bool is_iso) {
  fAcceptanceAngleVolumeNames = DictGetVecStr(puser_info, "volumes");
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();
  if (!fEnabledFlag)
    return;
  // (we cannot use py::dict here as it is lost at the end of the function)
  fAcceptanceAngleParam = DictToMap(puser_info);
  auto s = DictGetStr(puser_info, "skip_policy");
  fPolicy = AAUndefined;
  if (s == "ZeroEnergy")
    fPolicy = AAZeroEnergy;
  if (s == "SkipEvents")
    fPolicy = AASkipEvent;
  if (fPolicy == AAUndefined) {
    std::ostringstream oss;
    oss << "Unknown '" << s << "' mode for GateAcceptanceAngleTesterManager. "
        << "Expected: ZeroEnergy or SkipEvents";
    Fatal(oss.str());
  }

  // Cannot use SkipEvent with non iso source
  if (!is_iso && fPolicy == AASkipEvent) {
    std::ostringstream oss;
    oss << "Cannot use 'SkipEvent' mode without 'iso' direction type";
    Fatal(oss.str());
  }
}

void GateAcceptanceAngleTesterManager::InitializeAcceptanceAngle() {
  if (!fEnabledFlag)
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
  // Loop on all volume to check if it at least one volume is accepted
  for (auto *tester : fAATesters) {
    bool accept = tester->TestIfAccept(position, momentum_direction);
    if (accept)
      return true;
  }
  fNotAcceptedEvents++;
  if (fNotAcceptedEvents > fMaxNotAcceptedEvents) {
    std::ostringstream oss;
    oss << "Error, in AcceptanceAngleTest: " << fNotAcceptedEvents
        << " trials has been tested without accepted angle ; probably no "
           "possible direction here. Abort. ";
    Fatal(oss.str());
  }
  return false;
}

void GateAcceptanceAngleTesterManager::StartAcceptLoop() {
  if (!fEnabledFlag)
    return;
  fNotAcceptedEvents = 0;
  if (fAALastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
    InitializeAcceptanceAngle();
}
