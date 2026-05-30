/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTrackingAction.h"
#include "G4RunManager.hh"
#include "GateUserEventInformation.h"

GateTrackingAction::GateTrackingAction() : G4UserTrackingAction() {
  fUserEventInformationFlag = false;
}

void GateTrackingAction::RegisterActor(GateVActor *actor) {
  if (actor->HasAction("PreUserTrackingAction")) {
    fPreUserTrackingActionActors.push_back(actor);
  }
  if (actor->HasAction("PostUserTrackingAction")) {
    fPostUserTrackingActionActors.push_back(actor);
  }
}

void GateTrackingAction::RegisterAuxiliaryAttribute(
    GateVAuxiliaryAttribute *attribute) {
  if (attribute->HasAction("PreUserTrackingAction")) {
    fPreUserTrackingActionAttributes.push_back(attribute);
  }
  if (attribute->HasAction("PostUserTrackingAction")) {
    fPostUserTrackingActionAttributes.push_back(attribute);
  }
}

void GateTrackingAction::PreUserTrackingAction(const G4Track *track) {
  if (fUserEventInformationFlag) {
    const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto info =
        dynamic_cast<GateUserEventInformation *>(event->GetUserInformation());
    info->PreUserTrackingAction(track);
  }
  for (auto attribute : fPreUserTrackingActionAttributes) {
    attribute->PreUserTrackingAction(track);
  }
  for (auto actor : fPreUserTrackingActionActors) {
    actor->PreUserTrackingAction(track);
  }
}

void GateTrackingAction::PostUserTrackingAction(const G4Track *track) {
  for (auto attribute : fPostUserTrackingActionAttributes) {
    attribute->PostUserTrackingAction(track);
  }
  for (auto actor : fPostUserTrackingActionActors) {
    actor->PostUserTrackingAction(track);
  }
}
