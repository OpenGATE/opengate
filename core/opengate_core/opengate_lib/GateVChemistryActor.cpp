/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVChemistryActor.h"

GateVChemistryActor::GateVChemistryActor(py::dict &user_info, bool MT_ready)
    : GateVActor(user_info, MT_ready) {}

void GateVChemistryActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
}

bool GateVChemistryActor::IsChemistryTrackInsideAttachedVolume(
    const G4Track *track) const {
  if (track == nullptr || track->GetTouchable() == nullptr) {
    return false;
  }

  const auto &touchable = track->GetTouchableHandle();
  const auto depth = touchable->GetHistoryDepth();
  for (G4int i = 0; i <= depth; ++i) {
    const auto *volume = touchable->GetVolume(i);
    if (volume == nullptr) {
      continue;
    }
    const auto *logicalVolume = volume->GetLogicalVolume();
    if (logicalVolume == nullptr) {
      continue;
    }
    if (logicalVolume->GetName() == fAttachedToVolumeName) {
      return true;
    }
  }
  return false;
}

void GateVChemistryActor::StartChemistryTracking(G4Track *track) {
  (void)track;
}
