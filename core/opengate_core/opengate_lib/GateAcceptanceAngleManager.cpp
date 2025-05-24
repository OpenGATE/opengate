/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAcceptanceAngleManager.h"
#include "G4RunManager.hh"
#include "GateAcceptanceAngleSingleVolume.h"
#include "GateHelpersDict.h"

GateAcceptanceAngleManager::GateAcceptanceAngleManager() {
  fEnabledFlag = false;
  fNotAcceptedEvents = 0;
  fAALastRunId = -1;
  fPolicy = AASkipEvent;
  fMaxNotAcceptedEvents = 10000;
}

GateAcceptanceAngleManager::~GateAcceptanceAngleManager() {}

void GateAcceptanceAngleManager::Initialize(
    const std::map<std::string, std::string> &user_info, bool is_valid_type) {
  // AA is enabled if volumes is not empty and one of the flags is True
  // intersection_flag or normal_flag
  // fAcceptanceAngleVolumeNames = DictGetVecStr(user_info, "volumes");
  fAcceptanceAngleVolumeNames = GetVectorFromMapString(user_info, "volumes");
  fEnabledFlag = !fAcceptanceAngleVolumeNames.empty();

  bool b2 = StrToBool(user_info.at("intersection_flag"));
  bool b3 = StrToBool(user_info.at("normal_flag"));

  fEnabledFlag = fEnabledFlag && (b2 || b3);

  if (!fEnabledFlag)
    return;
  // (we cannot use py::dict here as it is lost at the end of the function)
  // fAcceptanceAngleParam = DictToMap(user_info);
  auto s = user_info.at("skip_policy");
  fMaxNotAcceptedEvents = StrToInt(user_info.at("max_rejection"));

  fPolicy = AAUndefined;
  if (s == "ZeroEnergy")
    fPolicy = AAZeroEnergy;
  if (s == "SkipEvents")
    fPolicy = AASkipEvent;
  if (fPolicy == AAUndefined) {
    std::ostringstream oss;
    oss << "Unknown '" << s << "' mode for GateAcceptanceAngleManager. "
        << "Expected: ZeroEnergy or SkipEvents";
    Fatal(oss.str());
  }

  // Cannot use SkipEvent with not a valid type of source
  if (!is_valid_type && fPolicy == AASkipEvent) {
    std::ostringstream oss;
    oss << "Cannot use 'SkipEvent' mode without 'iso' or 'histogram' direction "
           "type";
    Fatal(oss.str());
  }

  // copy for later
  fAcceptanceAngleParam = user_info;
}

void GateAcceptanceAngleManager::InitializeAcceptanceAngle() {
  if (!fEnabledFlag)
    return;
  // Create the testers (only the first time)
  if (fAATesters.empty()) {
    for (const auto &name : fAcceptanceAngleVolumeNames) {
      auto *t =
          new GateAcceptanceAngleSingleVolume(name, fAcceptanceAngleParam);
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

unsigned long GateAcceptanceAngleManager::GetNumberOfNotAcceptedEvents() const {
  return fNotAcceptedEvents;
}

bool GateAcceptanceAngleManager::TestIfAccept(
    const G4ThreeVector &position, const G4ThreeVector &momentum_direction) {
  if (!fEnabledFlag)
    return true;

  // Loop on all the volumes to check if it at least one volume is accepted
  for (const auto *tester : fAATesters) {
    bool accept = tester->TestIfAccept(position, momentum_direction);
    if (accept)
      return true;
  }
  if (fNotAcceptedEvents > fMaxNotAcceptedEvents) {
    std::ostringstream oss;
    oss << "Error, in AcceptanceAngleTest: " << fNotAcceptedEvents
        << " trials has been tested without accepted angle ; probably no "
           "possible direction here. Abort. ";
    Fatal(oss.str());
  }
  fNotAcceptedEvents++;
  return false;
}

void GateAcceptanceAngleManager::StartAcceptLoop() {
  if (!fEnabledFlag)
    return;
  fNotAcceptedEvents = 0;
  if (fAALastRunId !=
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID())
    InitializeAcceptanceAngle();
}
