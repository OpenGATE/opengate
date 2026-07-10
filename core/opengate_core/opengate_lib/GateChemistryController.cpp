/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChemistryController.h"
#include "GateHelpersDict.h"

#include <G4ITTrackHolder.hh>

GateChemistryController::GateChemistryController(py::dict &user_info)
    : GateVChemistryActor(user_info, true) {}

void GateChemistryController::InitializeUserInfo(py::dict &user_info) {
  GateVChemistryActor::InitializeUserInfo(user_info);
  fConfineChemistryToVolume =
      DictGetBool(user_info, "confine_chemistry_to_volume");
}

void GateChemistryController::StartChemistryTracking(G4Track *track) {
  if (track == nullptr || !fConfineChemistryToVolume) {
    return;
  }
  if (!IsChemistryTrackInsideAttachedVolume(track)) {
    G4ITTrackHolder::Instance()->PushToKill(track);
  }
}
