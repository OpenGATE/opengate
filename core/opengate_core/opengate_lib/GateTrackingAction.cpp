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
  auto actions = actor->fActions;
  auto beg = std::find(actions.begin(), actions.end(), "PreUserTrackingAction");
  if (beg != actions.end()) {
    fPreUserTrackingActionActors.push_back(actor);
  }
  auto end =
      std::find(actions.begin(), actions.end(), "PostUserTrackingAction");
  if (end != actions.end()) {
    fPostUserTrackingActionActors.push_back(actor);
  }
}

void GateTrackingAction::PreUserTrackingAction(const G4Track *track) {
  if (fUserEventInformationFlag) {
    const auto *event = G4RunManager::GetRunManager()->GetCurrentEvent();
    auto info =
        dynamic_cast<GateUserEventInformation *>(event->GetUserInformation());
    info->PreUserTrackingAction(track);
  }
  for (auto actor : fPreUserTrackingActionActors) {
    actor->PreUserTrackingAction(track);
  }
}

void GateTrackingAction::PostUserTrackingAction(const G4Track *track) {
  for (auto actor : fPostUserTrackingActionActors) {
    actor->PostUserTrackingAction(track);
  }
}
